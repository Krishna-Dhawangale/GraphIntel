export type DocumentStatus = "UPLOADED" | "PROCESSING" | "COMPLETED" | "FAILED";

export type UserRole = "USER" | "ANALYST" | "ADMIN";

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  role: UserRole;
  tenant_id: string;
  created_at: string;
}

export interface Document {
  id: string;
  user_id: string;
  tenant_id?: string;
  title: string;
  filename: string;
  file_size: number;
  content_type: string;
  storage_path: string;
  status: DocumentStatus;
  error_message: string | null;
  doc_metadata: Record<string, any>;
  created_at: string;
  updated_at: string;
  chunks_count?: number;
}

export interface DocumentChunk {
  id: string;
  document_id: string;
  chunk_index: number;
  text: string;
  page_number: number | null;
  section: string | null;
  token_count: number;
  chunk_metadata: Record<string, any>;
  created_at: string;
}

export interface SourceCitation {
  document_id: string;
  filename: string;
  page_number: number | null;
  section: string | null;
  chunk_id: string | null;
  citation_order: number;
  relevance_score: number;
  text_snippet?: string;
}

export interface RetrievedChunk {
  chunk_id: string;
  document_id: string;
  filename: string;
  text: string;
  page_number: number | null;
  section: string | null;
  score: number;
}

export interface GraphNode {
  id: string;
  label: string;
  type: string;
  metadata: Record<string, any>;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relationship: string;
  confidence: number;
  source_document?: string | null;
  valid_from?: number | null;
  valid_to?: number | null;
  metadata: Record<string, any>;
}

export interface GraphVisualizationResponse {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface GraphPathStep {
  node_name: string;
  node_type: string;
  relationship?: string;
  target_name?: string;
  confidence?: number;
  evidence_doc?: string;
}

export interface GraphPathInfo {
  length: number;
  nodes: string[];
  node_types: string[];
  relationships: string[];
  evidence_docs: string[];
}

export interface EvidenceItem {
  type: "vector" | "graph" | "metadata";
  content: string;
  entity?: string | null;
  relationship?: string | null;
  target?: string | null;
  source_document?: string | null;
  page?: number | null;
  confidence: number;
  valid_from?: number | null;
  valid_to?: number | null;
}

export interface QueryMetadata {
  retrieval_time_ms: number;
  llm_time_ms: number;
  total_time_ms: number;
  chunks_retrieved: number;
  model_used: string;
  graph_retrieval_time_ms?: number;
  vector_retrieval_time_ms?: number;
  rerank_time_ms?: number;
  paths_found?: number;
  graph_nodes_retrieved?: number;
  confidence_score?: number;
}

export interface QueryResponse {
  id?: string;
  question: string;
  answer: string;
  sources: SourceCitation[];
  retrieved_chunks: RetrievedChunk[];
  graph_paths?: GraphPathInfo[];
  entities?: string[];
  retrieval_mode?: string;
  evidence?: EvidenceItem[];
  metadata: QueryMetadata;
}

export interface QueryHistoryItem {
  id: string;
  question: string;
  answer: string;
  retrieval_time_ms: number;
  llm_time_ms: number;
  created_at: string;
  sources_count: number;
}

export interface ResearchReport {
  id: string;
  title: string;
  question: string;
  executive_summary: string;
  findings: string[];
  entities: string[];
  relationships: Array<{ source: string; rel: string; target: string; year?: number }>;
  graph_paths: GraphPathInfo[];
  evidence: EvidenceItem[];
  citations: SourceCitation[];
  confidence: number;
  methodology: string;
  limitations: string;
  created_at: string;
}

export interface AuditLogItem {
  id: string;
  user_id?: string;
  tenant_id?: string;
  action: string;
  resource_type?: string;
  resource_id?: string;
  status: string;
  ip_address?: string;
  user_agent?: string;
  metadata: Record<string, any>;
  created_at: string;
}
