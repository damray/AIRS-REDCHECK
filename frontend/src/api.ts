import { z } from "zod";

const API_BASE = "/api";
export const RESULTS_PAGE_SIZE = 25;

const nullableString = z.string().nullable();
const nullableStringWithMissingDefault: z.ZodType<
  string | null,
  z.ZodTypeDef,
  string | null | undefined
> = z
  .union([z.string(), z.null(), z.undefined()])
  .transform((value) => value ?? null);

export const importSummarySchema = z.object({
  dataset_id: z.string(),
  project_id: z.string(),
  scan_name: z.string(),
  detected_format: z.string(),
  stream_count: z.number(),
  attempt_count: z.number(),
  imported_count: z.number(),
  error_count: z.number(),
  status: z.string(),
});

export const resetDatasetsSchema = z.object({
  deleted_datasets: z.number(),
  deleted_attempts: z.number(),
});

export const datasetSchema = z.object({
  id: z.string(),
  project_id: z.string(),
  name: nullableString,
  scan_name: z.string(),
  source_filename: nullableString,
  source_content_type: z.string(),
  mapping_profile_id: nullableString,
  detected_format: z.string(),
  parser_version: z.string(),
  import_status: z.string(),
  stream_count: z.number(),
  attempt_count: z.number(),
  error_count: z.number(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const importErrorSchema = z.object({
  id: z.string(),
  dataset_id: z.string(),
  stream_id: nullableString,
  record_index: z.number().nullable(),
  iteration_key: nullableString,
  error_code: z.string(),
  message: z.string(),
  raw_payload: z.unknown().nullable(),
  created_at: z.string(),
});

export const projectSchema = z.object({
  id: z.string(),
  name: z.string(),
  is_archived: z.boolean(),
  import_count: z.number(),
  latest_activity_at: nullableString,
  archived_at: nullableString,
  created_at: z.string(),
  updated_at: z.string(),
});

export const resultAttemptSchema = z.object({
  attempt_id: z.string(),
  dataset_id: z.string(),
  stream_id: z.string(),
  external_stream_id: nullableString,
  input_type: z.string(),
  attempt_index: z.number(),
  source_prompt: z.string(),
  source_output: z.string(),
  source_verdict: nullableString,
  judge_verdict: nullableString,
  comparison_status: nullableString,
  review_decision: nullableString,
  reviewer_identity: nullableString,
  reviewed_at: nullableString,
  evaluation_error_code: nullableStringWithMissingDefault,
  evaluation_error_message: nullableStringWithMissingDefault,
  evaluation_error_created_at: nullableStringWithMissingDefault,
  severity: z.unknown().nullable(),
  category: z.unknown().nullable(),
  technique: z.unknown().nullable(),
  created_at: z.string(),
});

export const paginatedResultsSchema = z.object({
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
  items: z.array(resultAttemptSchema),
});

export const timelineSchema = z.object({
  stream_id: z.string(),
  external_stream_id: nullableString,
  input_type: z.string(),
  goal: nullableString,
  attempts: z.array(resultAttemptSchema),
});

export const triageSummarySchema = z.object({
  total_streams: z.number(),
  total_attempts: z.number(),
  processed_attempts: z.number(),
  remaining_attempts: z.number(),
  errors: z.number(),
  agreements: z.number(),
  disagreements: z.number(),
  source_stricter_than_judge: z.number(),
  judge_stricter_than_source: z.number(),
  uncertain: z.number(),
  review_required: z.number(),
  agent_streams: z.number(),
  static_streams: z.number(),
  average_attempts_per_stream: z.number(),
});

export const reviewedQualitySchema = z.object({
  total_attempts: z.number(),
  reviewed_cases: z.number(),
  alarm_threat_cases: z.number(),
  metric_cases: z.number(),
  review_coverage: z.number(),
  confirmed_tp: z.number(),
  confirmed_tn: z.number(),
  confirmed_fp: z.number(),
  confirmed_fn: z.number(),
  accuracy: z.number().nullable(),
  precision: z.number().nullable(),
  recall: z.number().nullable(),
  f1_score: z.number().nullable(),
});

export const humanReviewSchema = z.object({
  id: z.string(),
  dataset_id: z.string(),
  stream_id: z.string(),
  attempt_id: z.string(),
  decision: z.string(),
  reviewer_identity: z.string(),
  comment: nullableString,
  reviewed_at: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const portkeyProfileSchema = z.object({
  id: z.string(),
  profile_name: z.string(),
  gateway_base_url: z.string(),
  portkey_api_key_masked: z.string(),
  routing_mode: z.string(),
  provider_slug: nullableString,
  config_id: nullableString,
  judge_model: z.string(),
  temperature: z.number(),
  legacy_virtual_key_masked: nullableString,
  timeout_seconds: z.number(),
  metadata_tags: z.record(z.string()),
  created_at: z.string(),
  updated_at: z.string(),
});

export const promptProfileSchema = z.object({
  id: z.string(),
  name: z.string(),
  system_prompt: z.string(),
  rubric: z.string(),
  prompt_hash: z.string(),
  is_default: z.boolean(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const evaluationJobSchema = z.object({
  id: z.string(),
  dataset_id: z.string(),
  portkey_gateway_profile_id: z.string(),
  judge_prompt_profile_id: nullableString,
  prompt_hash: nullableString,
  model_name: nullableString,
  routing_mode: nullableString,
  provider_slug: nullableString,
  config_id: nullableString,
  timeout_seconds: z.number().nullable(),
  temperature: z.number().nullable(),
  status: z.string(),
  retry_limit: z.number(),
  total_attempts: z.number(),
  processed_attempts: z.number(),
  succeeded_attempts: z.number(),
  failed_attempts: z.number(),
  created_at: z.string(),
  updated_at: z.string(),
  started_at: nullableString,
  completed_at: nullableString,
});

export type ImportSummary = z.infer<typeof importSummarySchema>;
export type ResetDatasetsSummary = z.infer<typeof resetDatasetsSchema>;
export type Dataset = z.infer<typeof datasetSchema>;
export type Project = z.infer<typeof projectSchema>;
export type ImportErrorRecord = z.infer<typeof importErrorSchema>;
export type ResultAttempt = z.infer<typeof resultAttemptSchema>;
export type PaginatedResults = z.infer<typeof paginatedResultsSchema>;
export type StreamTimeline = z.infer<typeof timelineSchema>;
export type AutomatedTriageSummary = z.infer<typeof triageSummarySchema>;
export type ReviewedQualityMetrics = z.infer<typeof reviewedQualitySchema>;
export type HumanReview = z.infer<typeof humanReviewSchema>;
export type PortkeyProfile = z.infer<typeof portkeyProfileSchema>;
export type PromptProfile = z.infer<typeof promptProfileSchema>;
export type EvaluationJob = z.infer<typeof evaluationJobSchema>;
export type ReviewDecision =
  | "CONFIRM_SOURCE"
  | "CONFIRM_JUDGE"
  | "ALARM_THREAT";
export type ResultFilters = {
  comparisonStatus: string[];
  sourceVerdict: string;
  judgeVerdict: string;
  inputType: string;
  reviewed: string;
  reviewDecision: string;
  contextContains: string;
  outputContains: string;
};

export type PortkeyProfileInput = {
  profile_name: string;
  gateway_base_url: string;
  portkey_api_key?: string | null;
  routing_mode: "provider_slug" | "config_id";
  provider_slug: string | null;
  config_id: string | null;
  judge_model: string;
  temperature: number;
  legacy_virtual_key?: string | null;
  timeout_seconds: number;
  metadata_tags: Record<string, string>;
};

export type PromptProfileInput = {
  name: string;
  system_prompt: string;
  rubric: string;
  is_default: boolean;
};

export async function importDataset(input: {
  file: File;
  projectId?: string;
  projectName?: string;
  scanName?: string;
}): Promise<ImportSummary> {
  const params = new URLSearchParams({ filename: input.file.name });
  appendOptionalParam(params, "project_id", input.projectId ?? "");
  appendOptionalParam(params, "project_name", input.projectName ?? "");
  appendOptionalParam(params, "scan_name", input.scanName ?? "");
  const response = await fetch(
    `${API_BASE}/datasets/import?${params.toString()}`,
    {
      method: "POST",
      headers: {
        "Content-Type": input.file.type || contentTypeForFile(input.file.name),
      },
      body: input.file,
    },
  );
  return parseResponse(response, importSummarySchema);
}

export async function fetchProjects(): Promise<Project[]> {
  const response = await fetch(`${API_BASE}/projects`);
  return parseResponse(response, z.array(projectSchema));
}

export async function saveProject(input: {
  id?: string;
  name: string;
}): Promise<Project> {
  const response = await fetch(
    input.id ? `${API_BASE}/projects/${input.id}` : `${API_BASE}/projects`,
    {
      method: input.id ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: input.name }),
    },
  );
  return parseResponse(response, projectSchema);
}

export async function archiveProject(projectId: string): Promise<Project> {
  const response = await fetch(`${API_BASE}/projects/${projectId}`, {
    method: "DELETE",
  });
  return parseResponse(response, projectSchema);
}

export async function renameDatasetScan(input: {
  datasetId: string;
  scanName: string;
}): Promise<Dataset> {
  const response = await fetch(`${API_BASE}/datasets/${input.datasetId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ scan_name: input.scanName }),
  });
  return parseResponse(response, datasetSchema);
}

export async function fetchTriageSummary(
  projectId?: string,
): Promise<AutomatedTriageSummary> {
  const query = projectQuery(projectId);
  const response = await fetch(`${API_BASE}/results/triage-summary${query}`);
  return parseResponse(response, triageSummarySchema);
}

export async function fetchReviewedQuality(
  projectId?: string,
): Promise<ReviewedQualityMetrics> {
  const query = projectQuery(projectId);
  const response = await fetch(`${API_BASE}/results/reviewed-quality${query}`);
  return parseResponse(response, reviewedQualitySchema);
}

export async function fetchDatasets(projectId?: string): Promise<Dataset[]> {
  const query = projectQuery(projectId);
  const response = await fetch(`${API_BASE}/datasets${query}`);
  return parseResponse(response, z.array(datasetSchema));
}

export async function resetImportedDatasets(): Promise<ResetDatasetsSummary> {
  const response = await fetch(`${API_BASE}/datasets`, { method: "DELETE" });
  return parseResponse(response, resetDatasetsSchema);
}

export async function fetchImportErrors(
  datasetId: string,
  projectId?: string,
  offset = 0,
  limit = 25,
): Promise<ImportErrorRecord[]> {
  const params = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  });
  appendOptionalParam(params, "project_id", projectId ?? "");
  const response = await fetch(
    `${API_BASE}/datasets/${datasetId}/import-errors?${params.toString()}`,
  );
  return parseResponse(response, z.array(importErrorSchema));
}

export async function fetchPortkeyProfiles(): Promise<PortkeyProfile[]> {
  const response = await fetch(`${API_BASE}/portkey-gateway-profiles`);
  return parseResponse(response, z.array(portkeyProfileSchema));
}

export async function savePortkeyProfile(input: {
  id?: string;
  profile: PortkeyProfileInput;
}): Promise<PortkeyProfile> {
  const response = await fetch(
    input.id
      ? `${API_BASE}/portkey-gateway-profiles/${input.id}`
      : `${API_BASE}/portkey-gateway-profiles`,
    {
      method: input.id ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input.profile),
    },
  );
  return parseResponse(response, portkeyProfileSchema);
}

export async function testPortkeyProfile(profileId: string): Promise<{
  status: string;
  message: string;
  status_code: number | null;
}> {
  const response = await fetch(
    `${API_BASE}/portkey-gateway-profiles/${profileId}/test-connection`,
    { method: "POST" },
  );
  return parseResponse(
    response,
    z.object({
      status: z.string(),
      message: z.string(),
      status_code: z.number().nullable(),
    }),
  );
}

export async function fetchPromptProfiles(): Promise<PromptProfile[]> {
  const response = await fetch(`${API_BASE}/judge-prompt-profiles`);
  return parseResponse(response, z.array(promptProfileSchema));
}

export async function savePromptProfile(input: {
  id?: string;
  profile: PromptProfileInput;
}): Promise<PromptProfile> {
  const response = await fetch(
    input.id
      ? `${API_BASE}/judge-prompt-profiles/${input.id}`
      : `${API_BASE}/judge-prompt-profiles`,
    {
      method: input.id ? "PUT" : "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(input.profile),
    },
  );
  return parseResponse(response, promptProfileSchema);
}

export async function createEvaluationJob(input: {
  datasetId: string;
  portkeyProfileId: string;
  promptProfileId: string;
  retryLimit: number;
}): Promise<EvaluationJob> {
  const response = await fetch(`${API_BASE}/evaluation-jobs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      dataset_id: input.datasetId,
      portkey_gateway_profile_id: input.portkeyProfileId,
      judge_prompt_profile_id: input.promptProfileId,
      retry_limit: input.retryLimit,
    }),
  });
  return parseResponse(response, evaluationJobSchema);
}

export async function fetchEvaluationJobs(
  projectId?: string,
): Promise<EvaluationJob[]> {
  const query = projectQuery(projectId);
  const response = await fetch(`${API_BASE}/evaluation-jobs${query}`);
  return parseResponse(response, z.array(evaluationJobSchema));
}

export async function retryFailedEvaluationJob(
  jobId: string,
): Promise<EvaluationJob> {
  const response = await fetch(
    `${API_BASE}/evaluation-jobs/${jobId}/retry-failed`,
    {
      method: "POST",
    },
  );
  return parseResponse(response, evaluationJobSchema);
}

export async function fetchDisagreements(): Promise<PaginatedResults> {
  return fetchResults(defaultDisagreementFilters());
}

export async function fetchResults(
  filters: ResultFilters,
  offset = 0,
  limit = RESULTS_PAGE_SIZE,
  projectId?: string,
): Promise<PaginatedResults> {
  const params = resultFilterParams(filters);
  appendOptionalParam(params, "project_id", projectId ?? "");
  params.set("limit", String(limit));
  params.set("offset", String(offset));
  const response = await fetch(
    `${API_BASE}/results/attempts?${params.toString()}`,
  );
  return parseResponse(response, paginatedResultsSchema);
}

export function filteredExportUrl(
  filters: ResultFilters,
  projectId?: string,
): string {
  const params = resultFilterParams(filters);
  appendOptionalParam(params, "project_id", projectId ?? "");
  const query = params.toString();
  return `/api/results/export/current.csv${query.length > 0 ? `?${query}` : ""}`;
}

export function defaultDisagreementFilters(): ResultFilters {
  return {
    comparisonStatus: [
      "SOURCE_STRICTER_THAN_JUDGE",
      "JUDGE_STRICTER_THAN_SOURCE",
      "REVIEW_REQUIRED",
    ],
    sourceVerdict: "",
    judgeVerdict: "",
    inputType: "",
    reviewed: "",
    reviewDecision: "",
    contextContains: "",
    outputContains: "",
  };
}

export async function fetchTimeline(
  streamId: string,
  projectId?: string,
): Promise<StreamTimeline> {
  const query = projectQuery(projectId);
  const response = await fetch(
    `${API_BASE}/results/streams/${streamId}/timeline${query}`,
  );
  return parseResponse(response, timelineSchema);
}

export async function fetchAttemptDetail(
  attemptId: string,
  projectId?: string,
): Promise<ResultAttempt> {
  const query = projectQuery(projectId);
  const response = await fetch(
    `${API_BASE}/results/attempts/${attemptId}${query}`,
  );
  return parseResponse(response, resultAttemptSchema);
}

export async function submitReview(input: {
  attemptId: string;
  decision: ReviewDecision;
  reviewerIdentity: string;
  comment: string | null;
}): Promise<HumanReview> {
  const response = await fetch(
    `${API_BASE}/results/attempts/${input.attemptId}/review`,
    {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        decision: input.decision,
        reviewer_identity: input.reviewerIdentity,
        comment: input.comment,
      }),
    },
  );
  return parseResponse(response, humanReviewSchema);
}

async function parseResponse<T>(
  response: Response,
  schema: z.ZodType<T, z.ZodTypeDef, unknown>,
): Promise<T> {
  const text = await response.text();
  const payload = text.length > 0 ? JSON.parse(text) : null;
  if (!response.ok) {
    const detail =
      payload && typeof payload === "object" && "detail" in payload
        ? payload.detail
        : text;
    throw new Error(String(detail || response.statusText));
  }
  return schema.parse(payload);
}

function contentTypeForFile(fileName: string): string {
  if (fileName.toLowerCase().endsWith(".csv")) {
    return "text/csv";
  }
  return "application/json";
}

function resultFilterParams(filters: ResultFilters): URLSearchParams {
  const params = new URLSearchParams();
  filters.comparisonStatus.forEach((status) => {
    if (status.length > 0) {
      params.append("comparison_status", status);
    }
  });
  appendOptionalParam(params, "source_verdict", filters.sourceVerdict);
  appendOptionalParam(params, "judge_verdict", filters.judgeVerdict);
  appendOptionalParam(params, "input_type", filters.inputType);
  appendOptionalParam(params, "reviewed", filters.reviewed);
  appendOptionalParam(params, "review_decision", filters.reviewDecision);
  appendOptionalParam(params, "q", filters.contextContains);
  appendOptionalParam(params, "source_output_contains", filters.outputContains);
  return params;
}

function appendOptionalParam(
  params: URLSearchParams,
  key: string,
  value: string,
) {
  const trimmed = value.trim();
  if (trimmed.length > 0) {
    params.set(key, trimmed);
  }
}

function projectQuery(projectId?: string): string {
  const params = new URLSearchParams();
  appendOptionalParam(params, "project_id", projectId ?? "");
  const query = params.toString();
  return query.length > 0 ? `?${query}` : "";
}
