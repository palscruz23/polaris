"use client";

import { useDeferredValue, useEffect, useMemo, useState } from "react";

type TableSummary = {
  name: string;
  columns: string[];
  row_count: number;
};

type TablePage = TableSummary & {
  rows: Record<string, unknown>[];
  limit: number;
  offset: number;
  has_more: boolean;
};

const PAGE_SIZE = 25;

function isIdentifierColumn(column: string): boolean {
  return column === "id" || column.endsWith("_id");
}

function orderColumnsForDisplay(columns: string[]): string[] {
  const descriptiveColumns = columns.filter(
    (column) => !isIdentifierColumn(column),
  );
  const identifierColumns = columns.filter(isIdentifierColumn);

  return [...descriptiveColumns, ...identifierColumns];
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }

  if (typeof value === "object") {
    return JSON.stringify(value);
  }

  return String(value);
}

export default function DataTableBrowser() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  const [tables, setTables] = useState<TableSummary[]>([]);
  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [tablePage, setTablePage] = useState<TablePage | null>(null);
  const [columnFilters, setColumnFilters] = useState<Record<string, string>>({});
  const [offset, setOffset] = useState(0);
  const [isLoadingTables, setIsLoadingTables] = useState(Boolean(apiUrl));
  const [isLoadingRows, setIsLoadingRows] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const configurationError = apiUrl
    ? null
    : "NEXT_PUBLIC_API_URL is not configured.";
  const deferredColumnFilters = useDeferredValue(columnFilters);
  const filterEntries = useMemo(
    () =>
      Object.entries(deferredColumnFilters).filter(
        ([, value]) => value.trim().length > 0,
      ),
    [deferredColumnFilters],
  );
  const activeFilterCount = Object.values(columnFilters).filter(
    (value) => value.trim().length > 0,
  ).length;

  useEffect(() => {
    if (!apiUrl) {
      return;
    }

    let isActive = true;

    async function loadTables() {
      setIsLoadingTables(true);
      setError(null);

      try {
        const response = await fetch(`${apiUrl}/data/tables`);

        if (!response.ok) {
          throw new Error("Unable to load data tables.");
        }

        const data = (await response.json()) as TableSummary[];

        if (!isActive) {
          return;
        }

        setTables(data);
        setSelectedTable(data[0]?.name ?? null);
      } catch (loadError) {
        if (isActive) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Unable to load data tables.",
          );
        }
      } finally {
        if (isActive) {
          setIsLoadingTables(false);
        }
      }
    }

    loadTables();

    return () => {
      isActive = false;
    };
  }, [apiUrl]);

  useEffect(() => {
    if (!apiUrl || !selectedTable) {
      return;
    }

    let isActive = true;
    const apiBaseUrl = apiUrl;
    const tableName = selectedTable;

    async function loadRows() {
      setIsLoadingRows(true);
      setError(null);

      try {
        const params = new URLSearchParams({
          limit: String(PAGE_SIZE),
          offset: String(offset),
        });
        for (const [column, value] of filterEntries) {
          params.append("filter", `${column}=${value.trim()}`);
        }
        const response = await fetch(
          `${apiBaseUrl}/data/tables/${encodeURIComponent(tableName)}?${params}`,
        );

        if (!response.ok) {
          throw new Error("Unable to load table rows.");
        }

        const data = (await response.json()) as TablePage;

        if (isActive) {
          setTablePage(data);
        }
      } catch (loadError) {
        if (isActive) {
          setError(
            loadError instanceof Error
              ? loadError.message
              : "Unable to load table rows.",
          );
        }
      } finally {
        if (isActive) {
          setIsLoadingRows(false);
        }
      }
    }

    loadRows();

    return () => {
      isActive = false;
    };
  }, [apiUrl, selectedTable, offset, filterEntries]);

  const selectedSummary = useMemo(
    () => tables.find((table) => table.name === selectedTable) ?? null,
    [selectedTable, tables],
  );
  const currentStart = tablePage && tablePage.row_count > 0 ? offset + 1 : 0;
  const currentEnd = tablePage
    ? Math.min(offset + tablePage.rows.length, tablePage.row_count)
    : 0;
  const displayColumns = useMemo(
    () => (tablePage ? orderColumnsForDisplay(tablePage.columns) : []),
    [tablePage],
  );

  function selectTable(tableName: string) {
    setSelectedTable(tableName);
    setColumnFilters({});
    setOffset(0);
    setTablePage(null);
  }

  function updateColumnFilter(
    column: string,
    value: string,
  ) {
    setColumnFilters((currentFilters) => ({
      ...currentFilters,
      [column]: value,
    }));
    setOffset(0);
  }

  function clearFilters() {
    setColumnFilters({});
    setOffset(0);
  }

  return (
    <div className="data-browser">
      <aside className="data-table-list" aria-label="Postgres tables">
        <div className="data-panel-heading">
          <span>Tables</span>
          <strong>{tables.length}</strong>
        </div>

        {isLoadingTables ? (
          <p className="data-muted">Loading tables...</p>
        ) : null}

        {!isLoadingTables && tables.length === 0 && !error ? (
          <p className="data-muted">No tables found.</p>
        ) : null}

        <div className="data-table-buttons">
          {tables.map((table) => (
            <button
              className="data-table-button"
              data-active={table.name === selectedTable}
              key={table.name}
              onClick={() => selectTable(table.name)}
              type="button"
            >
              <span>{table.name}</span>
              <strong>{table.row_count}</strong>
            </button>
          ))}
        </div>
      </aside>

      <section className="data-table-view" aria-live="polite">
        {configurationError || error ? (
          <div className="data-error">{configurationError ?? error}</div>
        ) : null}

        {selectedSummary ? (
          <div className="data-table-toolbar">
            <div>
              <h2>{selectedSummary.name}</h2>
              <p>
                {selectedSummary.columns.length} columns ·{" "}
                {tablePage?.row_count ?? selectedSummary.row_count} rows
                {activeFilterCount > 0
                  ? ` filtered from ${selectedSummary.row_count}`
                  : ""}
              </p>
            </div>

            <div className="data-pagination">
              {activeFilterCount > 0 ? (
                <button
                  className="button button-secondary"
                  onClick={clearFilters}
                  type="button"
                >
                  Clear filters
                </button>
              ) : null}
              <button
                className="button button-secondary"
                disabled={offset === 0 || isLoadingRows}
                onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
                type="button"
              >
                Previous
              </button>
              <span>
                {currentStart}-{currentEnd}
              </span>
              <button
                className="button button-secondary"
                disabled={!tablePage?.has_more || isLoadingRows}
                onClick={() => setOffset(offset + PAGE_SIZE)}
                type="button"
              >
                Next
              </button>
            </div>
          </div>
        ) : null}

        <div className="data-table-shell" aria-busy={isLoadingRows}>
          {isLoadingRows ? (
            <p className="data-muted data-loading-status" role="status">
              Loading rows...
            </p>
          ) : null}

          {tablePage ? (
            <table className="data-table">
              <thead>
                <tr>
                  {displayColumns.map((column) => (
                    <th data-column={column} key={column}>
                      <span className="data-table-cell" title={column}>
                        {column}
                      </span>
                    </th>
                  ))}
                </tr>
                <tr className="data-filter-row">
                  {displayColumns.map((column) => (
                    <th data-column={column} key={`${column}-filter`}>
                      <label className="data-filter-control">
                        <span>Filter {column}</span>
                        <input
                          onChange={(event) =>
                            updateColumnFilter(column, event.target.value)
                          }
                          placeholder="Search"
                          type="search"
                          value={columnFilters[column] ?? ""}
                        />
                      </label>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {tablePage.rows.length > 0 ? (
                  tablePage.rows.map((row, rowIndex) => (
                    <tr key={`${tablePage.name}-${offset + rowIndex}`}>
                      {displayColumns.map((column) => {
                        const value = formatValue(row[column]);

                        return (
                          <td data-column={column} key={column}>
                            <span className="data-table-cell" title={value}>
                              {value}
                            </span>
                          </td>
                        );
                      })}
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td
                      className="data-empty-results"
                      colSpan={displayColumns.length}
                    >
                      {activeFilterCount > 0
                        ? "No rows match the current filters."
                        : "This table has no rows."}
                      </td>
                  </tr>
                )}
              </tbody>
            </table>
          ) : null}
        </div>
      </section>
    </div>
  );
}
