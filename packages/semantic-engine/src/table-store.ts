import type { RelationshipIR, SemanticModelIR, TableDataIR } from "@pbix2html/dir-schema";

export class TableStore {
  readonly model: SemanticModelIR;
  private readonly rowsByTable = new Map<string, Record<string, unknown>[]>();

  constructor(model: SemanticModelIR, data: TableDataIR[]) {
    this.model = model;
    for (const table of data) {
      this.rowsByTable.set(table.table, table.rows);
    }
  }

  rows(table: string): Record<string, unknown>[] {
    const rows = this.rowsByTable.get(table);
    if (!rows) {
      throw new Error(`Unknown table in DIR data manifest: ${table}`);
    }
    return rows;
  }

  rowCount(table: string): number {
    return this.rows(table).length;
  }

  distinctValues(table: string, column: string): unknown[] {
    const seen = new Set<unknown>();
    for (const row of this.rows(table)) {
      seen.add(row[column]);
    }
    return [...seen];
  }

  relationshipsFrom(table: string): RelationshipIR[] {
    return this.model.relationships.filter((r) => r.isActive && r.fromTable === table);
  }

  relationshipsTo(table: string): RelationshipIR[] {
    return this.model.relationships.filter((r) => r.isActive && r.toTable === table);
  }

  tableNames(): string[] {
    return this.model.tables.map((t) => t.name);
  }
}
