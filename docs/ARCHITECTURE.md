# Architecture

EDAViz is a single-process Streamlit app. There is no backend, database or API:
all data lives in the user's Streamlit session (`st.session_state`) and is lost
when the browser session ends.

## Request flow

Streamlit re-runs the whole script on every widget interaction:

```
streamlit run my_viz_plotly.py
        │
        ▼
my_viz_plotly.main()
  ├─ st.set_page_config(layout="wide", page_title="EDAViz App")
  ├─ sidebar option_menu: Home | Missing Data Imputation | Visualization | Time Series | About
  └─ lazy-import and call the selected view:
        views.home.home()
        views.missing_data.missing_data_imputation()
        views.visualization.visualization()
        views.time_series.time_series_analysis()
        views.about.about()
```

Views are imported lazily inside the `if/elif` so that heavy libraries (Prophet,
statsmodels) are only loaded when the Time Series page is opened.

## Local launcher

`edaviz/launcher.py` (the `edaviz` console script, `python -m edaviz`, and
`edaviz.show()`) does not import the app. It starts `sys.executable -m streamlit
run <installed my_viz_plotly.py>` as a child process bound to `127.0.0.1`, with
headless mode and a random `server.baseUrlPath` (`edaviz-<token>`) passed on the
command line, so config files cannot widen the bind address. The child runs with the app's
install directory as its working directory, so modules in the caller's directory
are not imported, and logs to a temporary file.

- **Port:** an explicit port must be free on `127.0.0.1` and `0.0.0.0`;
  otherwise the first free port from 8501 is used.
- **Readiness:** success is reported only after `<prefix>/_stcore/health`
  answers `ok`. The prefix means another server on the same port cannot satisfy
  the check. If the child exits or times out, `LaunchError` includes the log tail.
- **Shutdown:** `stop()` signals only the `Popen` it created (CTRL_BREAK on
  Windows in a separate process group, SIGTERM on POSIX), kills it after 10 s,
  and removes the log. An `atexit` hook stops servers left running. The CLI
  turns Ctrl+C, SIGTERM, SIGHUP, and SIGBREAK into the same shutdown.

## Modules

| File | Lines | Responsibility |
|---|---:|---|
| `my_viz_plotly.py` | 32 | Entry point and router |
| `edaviz/launcher.py` | 325 | Local launcher (CLI and `edaviz.show()`); not imported by the app |
| `views/home.py` | 295 | Load CSV (upload or GitHub URL), preprocessing operations, undo, preview, download |
| `views/missing_data.py` | 91 | Missing-value table, drop rows, KNN/mode imputation |
| `views/visualization.py` | 1596 | All general plots in one `visualization()` function with nested helpers |
| `views/time_series.py` | 1219 | Time series loader and ten analysis sections in one function |
| `views/about.py` | 256 | Static manual / marketing text |
| `utils/data_processing.py` | 60 | `apply_operations(raw_df, operations)` |
| `utils/plot_utils.py` | 0 | Contains only `import numpy` — unused |
| `visualization.py`, `time_series.py` (root) | 2630 / 1219 | Legacy copies, not imported anywhere |

## Session state

### Shared by Home / Missing Data / Visualization

| Key | Type | Meaning |
|---|---|---|
| `raw_df` | DataFrame | Data exactly as loaded |
| `filtered_df` | DataFrame | Current working dataset used by all other pages |
| `current_numeric_cols` | list[str] | Columns treated as numeric (recomputed from dtypes after each op) |
| `current_categorical_cols` | list[str] | Columns treated as categorical (`object`/`category` dtypes) |
| `operations` | list[dict] | Operation log for undo (only populated when tracking is on) |
| `enable_operation_tracking` | bool | Undo mode toggle |
| `data_loaded` | bool | Whether a dataset is present |
| `last_uploaded_file` | str | Filename / URL, used to detect a new upload |
| `is_imputed` | bool | Set by the Missing Data page |
| `viz_state` | dict | Remembered plot type and X/Y/Color/Facet/Size mapping |

### Time Series only

| Key | Meaning |
|---|---|
| `df` | Time-indexed DataFrame (date column parsed, sorted, set as index) |

The Time Series page **does not** read `filtered_df`; it has its own loader.

## Operation log and undo

Home and Missing Data can work in two modes:

- **Direct mode (default):** each button mutates `filtered_df` in place.
- **Tracking mode:** each action appends a dict to `operations`, and
  `filtered_df` is rebuilt as `apply_operations(raw_df, operations)`.
  “Undo Last Operation” pops the last entry and replays.

Supported operation types:

| `type` | Payload | Effect |
|---|---|---|
| `select_columns` | `columns` | Keep only these columns |
| `cast_types` | `numeric_cols`, `categorical_cols` | `pd.to_numeric(errors="coerce")` / cast to `str` |
| `subsample` | `sample_pct` | `df.sample(frac, random_state=42)` |
| `melt` | `id_vars` | Wide → long with `variable` / `value` columns |
| `date_features` | `date_column`, `dayfirst` | Adds Year, Month, Day, DayOfWeek, Hour |
| `remove_nan` | — | `dropna()` |
| `impute` | — | KNNImputer(k=5) on numeric, mode on categorical |

Note: the same transformation logic is written twice — once in
`apply_operations` and once inline in the views for direct mode. Any change must
be made in both places.

## Visualization page internals

- `PLOT_TYPES` lists the 15 plot types; it shrinks to 7 when there are no numeric columns.
- A row of seven selectors (plot type, X, Y, Color, Facet col, Facet row, Size) drives everything. Options depend on plot type; the sidebar “Risk It All” checkbox unlocks any column for any role.
- `render_plot()` dispatches on `plot_type`. Most branches use `render_side_by_side(config_fn, plot_fn)` to show plot-specific settings in a left column and the chart on the right.
- “missingno” plots (matrix, bars, heatmap, dendrogram) are re-implemented in Plotly/SciPy; the `missingno` package is not actually used.
- `check_cardinality()` warns when a color/facet column has more than 50 unique values.

## Time Series page internals

1. Sidebar menu picks one of ten sections. “Load Data” parses the chosen date
   column, drops unparseable rows, sorts and sets it as the index, then stores
   `st.session_state["df"]`.
2. For every other section a shared preamble reads sidebar options (variable(s),
   resample frequency, mean/sum, rolling window) and builds `df_summary`.
3. Each section renders from `df` or `df_summary`:

| Section | Technique |
|---|---|
| Time Series Visualization | Plotly lines, optional facets |
| Decomposition & ACF/PACF | `seasonal_decompose` or Prophet components; statsmodels ACF/PACF (matplotlib) |
| Anomaly Detection | `IsolationForest(contamination)` per variable |
| Temporal Profiles | Group by hour/weekday/month/quarter/year, box or line |
| Calendar Heatmap | `plotly_calheatmap` daily / hourly |
| Heatmap Profiles | Pivot heatmaps (month×year, hour×weekday, …) |
| Forecasting | Prophet with yearly/weekly/daily seasonality |
| Changepoint Analysis | Prophet changepoints, auto (percentile) or fixed N |
| Trend Analysis | Linear and degree-2 polynomial regression on the index |

## Deployment

`.github/workflows/` contains two near-identical Azure workflows (only the app
name and secret differ). Both run on push to `main`: set up Python 3.10, install
requirements, zip the repo, and deploy with `azure/webapps-deploy@v3`. No tests
are run. The Streamlit start command is configured in Azure, not in the repo.
