import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { App } from "./App";

const attempts = [
  {
    attempt_id: "attempt-agent-1",
    dataset_id: "dataset-1",
    stream_id: "stream-agent",
    external_stream_id: "agent-stream",
    input_type: "agent",
    attempt_index: 1,
    source_prompt: "Try to bypass policy",
    source_output: "Unsafe answer",
    source_verdict: "SAFE",
    judge_verdict: "THREAT",
    comparison_status: "JUDGE_STRICTER_THAN_SOURCE",
    review_decision: null,
    reviewer_identity: null,
    reviewed_at: null,
    evaluation_error_code: null,
    evaluation_error_message: null,
    evaluation_error_created_at: null,
    severity: "HIGH",
    category: "SECURITY",
    technique: ["ROLEPLAY"],
    created_at: "2026-06-04T00:00:00Z",
  },
  {
    attempt_id: "attempt-static-1",
    dataset_id: "dataset-1",
    stream_id: "stream-static",
    external_stream_id: null,
    input_type: "static",
    attempt_index: 0,
    source_prompt: "Static prompt",
    source_output: "Refusal",
    source_verdict: "THREAT",
    judge_verdict: "SAFE",
    comparison_status: "SOURCE_STRICTER_THAN_JUDGE",
    review_decision: "CONFIRM_SOURCE",
    reviewer_identity: "analyst",
    reviewed_at: "2026-06-04T00:01:00Z",
    evaluation_error_code: null,
    evaluation_error_message: null,
    evaluation_error_created_at: null,
    severity: "LOW",
    category: "SAFETY",
    technique: null,
    created_at: "2026-06-04T00:00:01Z",
  },
];

const errorAttempt = {
  attempt_id: "attempt-error-1",
  dataset_id: "dataset-1",
  stream_id: "stream-static-error",
  external_stream_id: null,
  input_type: "static",
  attempt_index: 0,
  source_prompt: "Static error prompt",
  source_output: "Gateway response could not be parsed",
  source_verdict: "SAFE",
  judge_verdict: null,
  comparison_status: "EVALUATION_ERROR",
  review_decision: null,
  reviewer_identity: null,
  reviewed_at: null,
  evaluation_error_code: "invalid_judge_response",
  evaluation_error_message: "Judge returned malformed JSON",
  evaluation_error_created_at: "2026-06-04T00:03:00Z",
  severity: "LOW",
  category: "SAFETY",
  technique: null,
  created_at: "2026-06-04T00:00:02Z",
};

const portkeyProfile = {
  id: "portkey-1",
  profile_name: "Main Judge",
  gateway_base_url: "https://api.portkey.ai",
  portkey_api_key_masked: "pk-t...alue",
  routing_mode: "provider_slug",
  provider_slug: "openai",
  config_id: null,
  judge_model: "gpt-test",
  temperature: 0.1,
  legacy_virtual_key_masked: null,
  timeout_seconds: 30,
  metadata_tags: {},
  created_at: "2026-06-04T00:00:00Z",
  updated_at: "2026-06-04T00:00:00Z",
};

const promptProfile = {
  id: "prompt-1",
  name: "Default safety Judge",
  system_prompt: "System prompt text",
  rubric: "Rubric text",
  prompt_hash: "a".repeat(64),
  is_default: true,
  created_at: "2026-06-04T00:00:00Z",
  updated_at: "2026-06-04T00:00:00Z",
};

const dataset = {
  id: "dataset-1",
  project_id: "project-1",
  name: null,
  scan_name: "Baseline scan",
  source_filename: "attacks.json",
  source_content_type: "application/json",
  mapping_profile_id: null,
  detected_format: "static_json",
  parser_version: "static-json-v1",
  import_status: "imported_with_errors",
  stream_count: 1,
  attempt_count: 2,
  error_count: 1,
  created_at: "2026-06-04T00:00:00Z",
  updated_at: "2026-06-04T00:00:00Z",
};

const evaluationJobs = [
  {
    id: "job-pending",
    dataset_id: "dataset-1",
    portkey_gateway_profile_id: "portkey-1",
    judge_prompt_profile_id: "prompt-1",
    prompt_hash: "a".repeat(64),
    model_name: "gpt-test",
    routing_mode: "provider_slug",
    provider_slug: "openai",
    config_id: null,
    timeout_seconds: 30,
    temperature: 0.1,
    status: "PENDING",
    retry_limit: 2,
    total_attempts: 10,
    processed_attempts: 2,
    succeeded_attempts: 2,
    failed_attempts: 0,
    created_at: "2026-06-04T00:00:00Z",
    updated_at: "2026-06-04T00:01:00Z",
    started_at: null,
    completed_at: null,
  },
  {
    id: "job-completed",
    dataset_id: "dataset-1",
    portkey_gateway_profile_id: "portkey-1",
    judge_prompt_profile_id: "prompt-1",
    prompt_hash: "a".repeat(64),
    model_name: "gpt-test",
    routing_mode: "provider_slug",
    provider_slug: "openai",
    config_id: null,
    timeout_seconds: 30,
    temperature: 0.1,
    status: "COMPLETED",
    retry_limit: 2,
    total_attempts: 2,
    processed_attempts: 2,
    succeeded_attempts: 2,
    failed_attempts: 0,
    created_at: "2026-06-04T00:02:00Z",
    updated_at: "2026-06-04T00:03:00Z",
    started_at: "2026-06-04T00:02:00Z",
    completed_at: "2026-06-04T00:03:00Z",
  },
  {
    id: "job-failed",
    dataset_id: "dataset-1",
    portkey_gateway_profile_id: "portkey-1",
    judge_prompt_profile_id: "prompt-1",
    prompt_hash: "a".repeat(64),
    model_name: "gpt-test",
    routing_mode: "provider_slug",
    provider_slug: "openai",
    config_id: null,
    timeout_seconds: 30,
    temperature: 0.1,
    status: "FAILED",
    retry_limit: 2,
    total_attempts: 3,
    processed_attempts: 3,
    succeeded_attempts: 1,
    failed_attempts: 2,
    created_at: "2026-06-04T00:04:00Z",
    updated_at: "2026-06-04T00:05:00Z",
    started_at: "2026-06-04T00:04:00Z",
    completed_at: "2026-06-04T00:05:00Z",
  },
  {
    id: "job-retrying",
    dataset_id: "dataset-1",
    portkey_gateway_profile_id: "portkey-1",
    judge_prompt_profile_id: "prompt-1",
    prompt_hash: "a".repeat(64),
    model_name: "gpt-test",
    routing_mode: "provider_slug",
    provider_slug: "openai",
    config_id: null,
    timeout_seconds: 30,
    temperature: 0.1,
    status: "RETRYING",
    retry_limit: 2,
    total_attempts: 4,
    processed_attempts: 1,
    succeeded_attempts: 1,
    failed_attempts: 0,
    created_at: "2026-06-04T00:06:00Z",
    updated_at: "2026-06-04T00:07:00Z",
    started_at: "2026-06-04T00:06:00Z",
    completed_at: null,
  },
];

const project = {
  id: "project-1",
  name: "Customer A",
  is_archived: false,
  import_count: 1,
  latest_activity_at: "2026-06-04T00:00:00Z",
  archived_at: null,
  created_at: "2026-06-04T00:00:00Z",
  updated_at: "2026-06-04T00:00:00Z",
};

let reviewedAttemptIds = new Set<string>();

describe("App", () => {
  beforeEach(() => {
    reviewedAttemptIds = new Set<string>();
    vi.stubGlobal("fetch", vi.fn(handleFetch));
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows the review queue with disagreement rows and opens attempt details", async () => {
    renderApp();

    const queue = await screen.findByLabelText("Disagreement results");
    await waitFor(() =>
      expect(within(queue).getByText("Unsafe answer")).toBeInTheDocument(),
    );
    await userEvent.click(within(queue).getByText("Unsafe answer"));

    const detailPanel = screen.getByLabelText("Attempt detail panel");
    expect(
      within(detailPanel).getAllByText("Try to bypass policy"),
    ).not.toHaveLength(0);
    expect(within(detailPanel).getByText("Unsafe answer")).toBeInTheDocument();
  });

  it("shows an ordered agent timeline for agent attempts", async () => {
    renderApp();

    const queue = await screen.findByLabelText("Disagreement results");
    await waitFor(() =>
      expect(within(queue).getByText("Unsafe answer")).toBeInTheDocument(),
    );
    await userEvent.click(within(queue).getByText("Unsafe answer"));

    expect(await screen.findByLabelText("Agent timeline")).toHaveTextContent(
      "Attempt 2",
    );
    expect(screen.getByLabelText("Agent timeline")).toHaveTextContent(
      "Attempt 3",
    );
    expect(screen.getByLabelText("Agent timeline")).toHaveTextContent(
      "Second attempt",
    );
  });

  it("submits adjudication for a selected disagreement", async () => {
    renderApp();
    const user = userEvent.setup();

    const queue = await screen.findByLabelText("Disagreement results");
    await waitFor(() =>
      expect(within(queue).getByText("Unsafe answer")).toBeInTheDocument(),
    );
    await user.click(within(queue).getByText("Unsafe answer"));
    await user.clear(screen.getByLabelText("Comment"));
    await user.type(screen.getByLabelText("Comment"), "Judge is correct");
    await user.click(screen.getByRole("button", { name: /^Confirm Judge/ }));

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/api/results/attempts/attempt-agent-1/review",
        expect.objectContaining({
          method: "PUT",
        }),
      );
    });
    expect(await screen.findByText("Review saved")).toBeInTheDocument();
    await waitFor(() => {
      expect(
        within(queue).getByRole("button", { name: /Review required/ }),
      ).toHaveTextContent("0");
    });
  });

  it("shows a checked review decision box for adjudicated attempts", async () => {
    renderApp();
    const user = userEvent.setup();

    const queue = await screen.findByLabelText("Disagreement results");
    await user.click(
      within(queue).getByRole("button", { name: /Review required/ }),
    );
    const reviewedCheckbox = await within(queue).findByLabelText(
      "Review decision made for attempt-static-1",
    );
    expect(reviewedCheckbox).toBeChecked();

    await user.click(within(queue).getByText("Refusal"));

    expect(screen.getByLabelText("Review decision made")).toBeChecked();
  });

  it("renders triage dashboard with summary metrics", async () => {
    renderApp();
    const user = userEvent.setup();

    await user.click(screen.getByTitle("Triage"));

    const dashboard = await screen.findByLabelText("Dashboard summaries");
    await waitFor(() =>
      expect(
        within(dashboard).getByText("Triage overview"),
      ).toBeInTheDocument(),
    );
    expect(
      within(dashboard).getByText("Comparison breakdown"),
    ).toBeInTheDocument();
  });

  it("filters evaluation errors from triage and clears back", async () => {
    renderApp();
    const user = userEvent.setup();

    await user.click(screen.getByTitle("Triage"));
    const dashboard = await screen.findByLabelText("Dashboard summaries");

    await waitFor(() =>
      expect(
        within(dashboard).getByRole("button", {
          name: /View evaluation errors/,
        }),
      ).toBeInTheDocument(),
    );
    await user.click(
      within(dashboard).getByRole("button", {
        name: /View evaluation errors/,
      }),
    );

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/api/results/attempts?comparison_status=EVALUATION_ERROR&reviewed=false&limit=25&offset=0",
      );
    });

    const reviewArea = await screen.findByLabelText("Disagreement results");
    await waitFor(() =>
      expect(
        within(reviewArea).getByText("Gateway response could not be parsed"),
      ).toBeInTheDocument(),
    );

    await user.click(
      within(reviewArea).getByText("Gateway response could not be parsed"),
    );
    const detailPanel = screen.getByLabelText("Attempt detail panel");
    expect(
      within(detailPanel).getByText("invalid_judge_response"),
    ).toBeInTheDocument();
    expect(
      within(detailPanel).getByText("Judge returned malformed JSON"),
    ).toBeInTheDocument();

    await user.click(within(reviewArea).getByRole("button", { name: /Clear/ }));
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/api/results/attempts?limit=25&offset=0",
      );
    });
  });

  it("uploads a file from the datasets view", async () => {
    renderApp();
    const user = userEvent.setup();

    await user.click(screen.getByTitle("Datasets"));
    const file = new File(
      ['[{"prompt":"p","output":"o","threat":false}]'],
      "attacks.json",
      { type: "application/json" },
    );

    await user.upload(screen.getByLabelText("Upload red-team export"), file);

    expect(await screen.findByLabelText("Import summary")).toHaveTextContent(
      "static_json",
    );
    expect(screen.getByLabelText("Import summary")).toHaveTextContent(
      "1 imported",
    );
  });

  it("selects a project workspace for result queries", async () => {
    renderApp();
    const user = userEvent.setup();

    await screen.findByRole("option", { name: "Customer A" });
    await user.selectOptions(
      screen.getByLabelText("Project workspace"),
      "project-1",
    );

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/api/results/attempts?comparison_status=SOURCE_STRICTER_THAN_JUDGE&comparison_status=JUDGE_STRICTER_THAN_SOURCE&comparison_status=REVIEW_REQUIRED&reviewed=false&project_id=project-1&limit=25&offset=0",
      );
    });
  });

  it("renames a project and scan then archives the project", async () => {
    renderApp();
    const user = userEvent.setup();

    await user.click(screen.getByTitle("Datasets"));
    await screen.findByRole("option", { name: "Customer A (1 imports)" });
    await user.selectOptions(
      screen.getByLabelText("Current project"),
      "project-1",
    );
    await user.type(screen.getByLabelText("Rename project"), "Customer B");
    await user.click(screen.getByRole("button", { name: /Rename project/ }));

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/api/projects/project-1",
        expect.objectContaining({ method: "PUT" }),
      );
    });

    await screen.findByRole("option", { name: "Baseline scan (1 errors)" });
    await user.selectOptions(screen.getByLabelText("Dataset"), "dataset-1");
    await user.type(screen.getByLabelText("Rename scan"), "Retest scan");
    await user.click(screen.getByRole("button", { name: /Rename scan/ }));

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/api/datasets/dataset-1",
        expect.objectContaining({ method: "PUT" }),
      );
    });

    await user.click(screen.getByRole("button", { name: /Archive project/ }));
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/api/projects/project-1",
        expect.objectContaining({ method: "DELETE" }),
      );
    });
  });

  it("creates, updates, and tests Portkey profiles in config view", async () => {
    renderApp();
    const user = userEvent.setup();

    await user.click(screen.getByTitle("Judge config"));

    const settings = await screen.findByLabelText("Portkey settings");
    await within(settings).findByRole("option", { name: "Main Judge" });
    await user.selectOptions(
      within(settings).getByLabelText("Saved profile"),
      "portkey-1",
    );
    expect(within(settings).getByDisplayValue("gpt-test")).toBeInTheDocument();
    expect(screen.queryByText("pk-test-secret-value")).not.toBeInTheDocument();

    await user.clear(within(settings).getByDisplayValue("gpt-test"));
    await user.type(
      within(settings).getByLabelText("Judge model"),
      "gpt-updated",
    );
    await user.click(screen.getByRole("button", { name: "Save profile" }));

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/api/portkey-gateway-profiles/portkey-1",
        expect.objectContaining({ method: "PUT" }),
      );
    });
    await user.click(screen.getByRole("button", { name: "Test connection" }));
    expect(
      await screen.findByText("ok: Gateway connection succeeded. (HTTP 200)"),
    ).toBeInTheDocument();
  });

  it("shows and edits prompt profiles with a visible hash in config view", async () => {
    renderApp();
    const user = userEvent.setup();

    await user.click(screen.getByTitle("Judge config"));

    const settings = await screen.findByLabelText("Prompt settings");
    await within(settings).findByRole("option", {
      name: "Default safety Judge (default)",
    });
    await user.selectOptions(
      within(settings).getByLabelText("Saved prompt"),
      "prompt-1",
    );
    expect(
      within(settings).getByDisplayValue("System prompt text"),
    ).toBeInTheDocument();
    expect(
      within(settings).getByText(`hash · ${"a".repeat(64)}`),
    ).toBeInTheDocument();

    await user.clear(within(settings).getByDisplayValue("Rubric text"));
    await user.type(
      within(settings).getByLabelText("Rubric"),
      "Updated rubric",
    );
    await user.click(screen.getByRole("button", { name: "Save prompt" }));

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/api/judge-prompt-profiles/prompt-1",
        expect.objectContaining({ method: "PUT" }),
      );
    });
  });

  it("starts an evaluation job from the datasets view", async () => {
    renderApp();
    const user = userEvent.setup();

    await user.click(screen.getByTitle("Datasets"));

    await screen.findByRole("option", { name: "Main Judge" });
    await screen.findByRole("option", {
      name: "Default safety Judge (default)",
    });
    await screen.findByRole("option", { name: "Baseline scan (1 errors)" });

    await user.selectOptions(screen.getByLabelText("Dataset"), "dataset-1");
    await user.selectOptions(
      screen.getByLabelText("Portkey profile"),
      "portkey-1",
    );
    await user.selectOptions(
      screen.getByLabelText("Prompt profile"),
      "prompt-1",
    );
    await user.click(screen.getByRole("button", { name: /Run evaluation/ }));

    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/api/evaluation-jobs",
        expect.objectContaining({ method: "POST" }),
      );
    });
    expect(await screen.findByText(/Job PENDING/)).toBeInTheDocument();
  });

  it("shows scan and project evaluation progress states", async () => {
    renderApp();
    const user = userEvent.setup();

    await user.click(screen.getByTitle("Datasets"));

    const progress = await screen.findByLabelText("Evaluation progress");
    const rollup = within(progress).getByLabelText("Project evaluation rollup");
    expect(rollup).toHaveTextContent("8 / 19 processed");
    expect(rollup).toHaveTextContent("6 succeeded");
    expect(rollup).toHaveTextContent("2 failed");
    expect(rollup).toHaveTextContent("11 remaining");
    expect(within(progress).getByText("Baseline scan")).toBeInTheDocument();
    expect(within(progress).getByText("PENDING")).toBeInTheDocument();
    expect(within(progress).getByText("COMPLETED")).toBeInTheDocument();
    expect(within(progress).getByText("FAILED")).toBeInTheDocument();
    expect(within(progress).getByText("RETRYING")).toBeInTheDocument();
    expect(
      within(progress).getByRole("button", { name: /Retry failed/ }),
    ).toBeInTheDocument();
    expect(within(progress).queryByText("Try to bypass policy")).toBeNull();
    expect(within(progress).queryByText("pk-test-secret-value")).toBeNull();

    await user.click(
      within(progress).getByRole("button", { name: /Retry failed/ }),
    );
    await waitFor(() => {
      expect(fetch).toHaveBeenCalledWith(
        "/api/evaluation-jobs/job-failed/retry-failed",
        expect.objectContaining({ method: "POST" }),
      );
    });
  });

  it("shows paginated import errors in the datasets view", async () => {
    renderApp();
    const user = userEvent.setup();

    await user.click(screen.getByTitle("Datasets"));
    await screen.findByRole("option", { name: "Baseline scan (1 errors)" });
    await user.selectOptions(screen.getByLabelText("Dataset"), "dataset-1");

    const errorMenu = await screen.findByLabelText("Import error menu");
    expect(
      within(errorMenu).getByText("missing_required_fields"),
    ).toBeInTheDocument();
    expect(within(errorMenu).getByText("Record 2")).toBeInTheDocument();
    expect(within(errorMenu).getByText(/prompt/)).toBeInTheDocument();
  });

  it("shows export link for current view in review", async () => {
    renderApp();

    const detailPanel = await screen.findByLabelText("Attempt detail panel");
    await waitFor(() =>
      expect(screen.getByText("Unsafe answer")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByText("Unsafe answer"));

    await waitFor(() =>
      expect(
        within(screen.getByLabelText("Attempt detail panel")).getByRole(
          "link",
          { name: /Export current view/ },
        ),
      ).toBeInTheDocument(),
    );
  });
});

function renderApp() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>,
  );
}

function handleFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const url = String(input);
  if (url === "/api/datasets" && init?.method === "DELETE") {
    return jsonResponse({ deleted_datasets: 1, deleted_attempts: 2 });
  }
  if (url.startsWith("/api/results/triage-summary")) {
    return jsonResponse({
      total_streams: 2,
      total_attempts: 2,
      processed_attempts: 2,
      remaining_attempts: 0,
      errors: 1,
      agreements: 0,
      disagreements: 2,
      source_stricter_than_judge: 1,
      judge_stricter_than_source: 1,
      uncertain: 0,
      review_required: 0,
      agent_streams: 1,
      static_streams: 1,
      average_attempts_per_stream: 1,
    });
  }
  if (url.startsWith("/api/results/reviewed-quality")) {
    return jsonResponse({
      total_attempts: 2,
      reviewed_cases: 1,
      ambiguous_cases: 0,
      metric_cases: 1,
      review_coverage: 0.5,
      confirmed_tp: 1,
      confirmed_tn: 0,
      confirmed_fp: 0,
      confirmed_fn: 0,
      accuracy: 1,
      precision: 1,
      recall: 1,
      f1_score: 1,
    });
  }
  if (url === "/api/projects") {
    return jsonResponse([project]);
  }
  if (url === "/api/projects/project-1" && init?.method === "PUT") {
    return jsonResponse({ ...project, name: "Customer B" });
  }
  if (url === "/api/projects/project-1" && init?.method === "DELETE") {
    return jsonResponse({
      ...project,
      is_archived: true,
      archived_at: "2026-06-04T00:05:00Z",
    });
  }
  if (url === "/api/datasets") {
    return jsonResponse([dataset]);
  }
  if (url === "/api/datasets?project_id=project-1") {
    return jsonResponse([dataset]);
  }
  if (url === "/api/datasets/dataset-1" && init?.method === "PUT") {
    return jsonResponse({ ...dataset, scan_name: "Retest scan" });
  }
  if (url.startsWith("/api/datasets/dataset-1/import-errors")) {
    return jsonResponse([
      {
        id: "error-1",
        dataset_id: "dataset-1",
        stream_id: null,
        record_index: 2,
        iteration_key: null,
        error_code: "missing_required_fields",
        message: "Missing prompt",
        raw_payload: { output: "o" },
        created_at: "2026-06-04T00:00:00Z",
      },
    ]);
  }
  if (url === "/api/portkey-gateway-profiles") {
    if (init?.method === "POST") {
      return jsonResponse(portkeyProfile);
    }
    return jsonResponse([portkeyProfile]);
  }
  if (
    url === "/api/portkey-gateway-profiles/portkey-1" &&
    init?.method === "PUT"
  ) {
    return jsonResponse({
      ...portkeyProfile,
      judge_model: "gpt-updated",
      temperature: 0.2,
    });
  }
  if (url === "/api/portkey-gateway-profiles/portkey-1/test-connection") {
    return jsonResponse({
      status: "ok",
      message: "Gateway connection succeeded.",
      status_code: 200,
    });
  }
  if (url === "/api/judge-prompt-profiles") {
    if (init?.method === "POST") {
      return jsonResponse(promptProfile);
    }
    return jsonResponse([promptProfile]);
  }
  if (url === "/api/judge-prompt-profiles/prompt-1" && init?.method === "PUT") {
    return jsonResponse({
      ...promptProfile,
      rubric: "Updated rubric",
      prompt_hash: "b".repeat(64),
    });
  }
  if (url === "/api/evaluation-jobs" && init?.method === "POST") {
    return jsonResponse({
      id: "job-1",
      dataset_id: "dataset-1",
      portkey_gateway_profile_id: "portkey-1",
      judge_prompt_profile_id: "prompt-1",
      prompt_hash: "a".repeat(64),
      model_name: "gpt-test",
      routing_mode: "provider_slug",
      provider_slug: "openai",
      config_id: null,
      timeout_seconds: 30,
      temperature: 0.1,
      status: "PENDING",
      retry_limit: 2,
      total_attempts: 2,
      processed_attempts: 0,
      succeeded_attempts: 0,
      failed_attempts: 0,
      created_at: "2026-06-04T00:00:00Z",
      updated_at: "2026-06-04T00:00:00Z",
      started_at: null,
      completed_at: null,
    });
  }
  if (url === "/api/evaluation-jobs/job-failed/retry-failed") {
    return jsonResponse({
      ...evaluationJobs[2],
      status: "RETRYING",
      processed_attempts: 1,
      succeeded_attempts: 1,
      failed_attempts: 0,
      completed_at: null,
    });
  }
  if (
    url === "/api/evaluation-jobs" ||
    url === "/api/evaluation-jobs?project_id=project-1"
  ) {
    return jsonResponse(evaluationJobs);
  }
  if (url.startsWith("/api/results/attempts?")) {
    if (url.includes("comparison_status=EVALUATION_ERROR")) {
      return jsonResponse({
        total: 1,
        limit: 25,
        offset: 0,
        items: [errorAttempt],
      });
    }
    const effectiveAttempts = attempts.map((attempt) =>
      reviewedAttemptIds.has(attempt.attempt_id)
        ? {
            ...attempt,
            review_decision: "CONFIRM_JUDGE",
            reviewer_identity: "analyst",
            reviewed_at: "2026-06-04T00:02:00Z",
          }
        : attempt,
    );
    if (url.includes("reviewed=false")) {
      const unreviewedAttempts = effectiveAttempts.filter(
        (a) => !a.review_decision,
      );
      return jsonResponse({
        total: unreviewedAttempts.length,
        limit: 25,
        offset: 0,
        items: unreviewedAttempts,
      });
    }
    return jsonResponse({
      total: effectiveAttempts.length,
      limit: 25,
      offset: 0,
      items: effectiveAttempts,
    });
  }
  if (url === "/api/results/attempts/attempt-agent-1") {
    return jsonResponse(
      reviewedAttemptIds.has("attempt-agent-1")
        ? {
            ...attempts[0],
            review_decision: "CONFIRM_JUDGE",
            reviewer_identity: "analyst",
            reviewed_at: "2026-06-04T00:02:00Z",
          }
        : attempts[0],
    );
  }
  if (url === "/api/results/attempts/attempt-static-1") {
    return jsonResponse(attempts[1]);
  }
  if (url === "/api/results/attempts/attempt-error-1") {
    return jsonResponse(errorAttempt);
  }
  if (url.startsWith("/api/results/streams/stream-agent/timeline")) {
    return jsonResponse({
      stream_id: "stream-agent",
      external_stream_id: "agent-stream",
      input_type: "agent",
      goal: "Find a bypass",
      attempts: [
        attempts[0],
        {
          ...attempts[0],
          attempt_id: "attempt-agent-2",
          attempt_index: 2,
          source_prompt: "Second attempt",
        },
      ],
    });
  }
  if (
    url.startsWith("/api/results/attempts/attempt-agent-1/review") &&
    init?.method === "PUT"
  ) {
    reviewedAttemptIds.add("attempt-agent-1");
    return jsonResponse({
      id: "review-1",
      dataset_id: "dataset-1",
      stream_id: "stream-agent",
      attempt_id: "attempt-agent-1",
      decision: "CONFIRM_JUDGE",
      reviewer_identity: "analyst",
      comment: "Judge is correct",
      reviewed_at: "2026-06-04T00:02:00Z",
      created_at: "2026-06-04T00:02:00Z",
      updated_at: "2026-06-04T00:02:00Z",
    });
  }
  if (url.startsWith("/api/datasets/import")) {
    return jsonResponse({
      dataset_id: "dataset-2",
      project_id: "project-2",
      scan_name: "attacks scan 20260604-000000",
      detected_format: "static_json",
      stream_count: 1,
      attempt_count: 1,
      imported_count: 1,
      error_count: 0,
      status: "imported",
    });
  }
  throw new Error(`Unhandled fetch: ${url}`);
}

function jsonResponse(payload: unknown): Promise<Response> {
  return Promise.resolve(
    new Response(JSON.stringify(payload), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}
