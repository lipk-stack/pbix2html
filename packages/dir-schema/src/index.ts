export type FidelityClassification =
  | "EXACT"
  | "SEMANTICALLY_EQUIVALENT"
  | "VISUALLY_EQUIVALENT"
  | "APPROXIMATED"
  | "SNAPSHOTTED"
  | "CONNECTED_RUNTIME_REQUIRED"
  | "UNSUPPORTED"
  | "BLOCKED_FOR_SECURITY"
  | "BLOCKED_FOR_LICENSING";

export interface Rect {
  x: number;
  y: number;
  width: number;
  height: number;
}

export type ColumnType = "string" | "number" | "boolean" | "date" | "dateTime";

export interface ColumnIR {
  name: string;
  dataType: ColumnType;
  isHidden?: boolean;
  formatString?: string;
  sortByColumn?: string;
}

export interface TableIR {
  name: string;
  columns: ColumnIR[];
  isHidden?: boolean;
  isDateTable?: boolean;
}

export type CrossFilterDirection = "single" | "both";
export type RelationshipCardinality = "oneToMany" | "manyToOne" | "oneToOne" | "manyToMany";

export interface RelationshipIR {
  id: string;
  fromTable: string;
  fromColumn: string;
  toTable: string;
  toColumn: string;
  crossFilterDirection: CrossFilterDirection;
  isActive: boolean;
  cardinality: RelationshipCardinality;
}

export interface ColumnRef {
  table: string;
  column: string;
}

/**
 * Structured, non-textual subset of DAX evaluation semantics. This is a typed
 * expression tree, not a DAX text parser — see docs/DAX_SUPPORT.md for the
 * distinction and current coverage (a handful of aggregations + CALCULATE-style
 * filter override). A real DAX lexer/parser/binder is future work (roadmap).
 */
export type AggregationFunction =
  | "SUM"
  | "AVERAGE"
  | "COUNT"
  | "COUNTROWS"
  | "DISTINCTCOUNT"
  | "MIN"
  | "MAX";

export type MeasureExpressionIR =
  | { kind: "aggregation"; fn: AggregationFunction; column?: ColumnRef }
  | {
      kind: "divide";
      numerator: MeasureExpressionIR;
      denominator: MeasureExpressionIR;
      alternateResult?: number;
    }
  | { kind: "measureRef"; measure: string }
  | { kind: "calculate"; expression: MeasureExpressionIR; filters: FilterExpressionIR[] }
  | {
      kind: "binaryOp";
      op: "+" | "-" | "*" | "/";
      left: MeasureExpressionIR;
      right: MeasureExpressionIR;
    };

export interface MeasureIR {
  name: string;
  table: string;
  expression: MeasureExpressionIR;
  formatString?: string;
  displayFolder?: string;
  isHidden?: boolean;
}

export interface SemanticModelIR {
  tables: TableIR[];
  relationships: RelationshipIR[];
  measures: MeasureIR[];
}

export type FilterOperator = "in" | "notIn" | "equals" | "between" | "topN" | "and" | "or";

export interface FilterExpressionIR {
  operator: FilterOperator;
  target?: ColumnRef;
  values?: unknown[];
  operands?: FilterExpressionIR[];
}

export interface AppliedFilterIR {
  id: string;
  scope: "report" | "page" | "visual";
  expression: FilterExpressionIR;
  isLockedByUser?: boolean;
}

export type NormalizedVisualType =
  | "card"
  | "multiRowCard"
  | "barChart"
  | "columnChart"
  | "lineChart"
  | "pieChart"
  | "donutChart"
  | "table"
  | "matrix"
  | "slicer"
  | "textBox"
  | "image"
  | "shape"
  | "button"
  | "pageNavigator"
  | "unsupported";

export interface DataBindingIR {
  category?: ColumnRef[];
  values?: (ColumnRef | { measure: string })[];
  series?: ColumnRef[];
}

export interface FormatIR {
  title?: string;
  showTitle?: boolean;
  backgroundColor?: string;
  fontColor?: string;
  fontFamily?: string;
  fontSize?: number;
  numberFormat?: string;
}

export type VisualInteractionMode = "filter" | "highlight" | "none" | "navigate" | "drill";

export interface VisualInteractionIR {
  targetVisualId: string;
  mode: VisualInteractionMode;
}

export interface VisualIR {
  id: string;
  sourceType: string;
  normalizedType: NormalizedVisualType;
  bounds: Rect;
  zIndex: number;
  bindings: DataBindingIR;
  format: FormatIR;
  filters: AppliedFilterIR[];
  interactions: VisualInteractionIR[];
  fidelity: FidelityClassification;
  slicerField?: ColumnRef;
}

export interface PageIR {
  id: string;
  name: string;
  displayName: string;
  width: number;
  height: number;
  visibility: "visible" | "hidden" | "tooltip";
  filters: AppliedFilterIR[];
  visuals: VisualIR[];
}

export interface InteractionEdge {
  sourceVisualId: string;
  targetVisualId: string;
  mode: VisualInteractionMode;
}

export interface InteractionGraph {
  edges: InteractionEdge[];
}

export type SourceStorageMode = "import" | "directQuery" | "liveConnection" | "directLake" | "composite";

export interface SourceDescriptor {
  originalFormat: "pbix" | "pbip" | "structured-fixture";
  adapterId: string;
  storageMode: SourceStorageMode;
  ingestedAt?: string;
}

export interface ProvenanceRecord {
  targetObjectId: string;
  sourceObjectId?: string;
  transformationPasses: string[];
  translatorVersion: string;
  fidelity: FidelityClassification;
  warnings: string[];
}

export interface CompatibilityItem {
  objectId: string;
  objectType: string;
  status: FidelityClassification;
  notes?: string;
}

export interface CompatibilityManifest {
  overallFidelity: FidelityClassification;
  items: CompatibilityItem[];
}

export interface TableDataIR {
  table: string;
  rows: Record<string, unknown>[];
}

export interface DataManifest {
  tables: TableDataIR[];
  snapshotTimestamp: string;
}

export interface DashboardIR {
  irVersion: string;
  source: SourceDescriptor;
  reportName: string;
  semanticModel: SemanticModelIR;
  data: DataManifest;
  pages: PageIR[];
  interactions: InteractionGraph;
  compatibility: CompatibilityManifest;
  provenance: ProvenanceRecord[];
}

export const DIR_VERSION = "0.1.0";
