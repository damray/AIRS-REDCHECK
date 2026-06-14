import { afterEach, describe, expect, it, vi } from "vitest";

import { evaluationJobSchema, importDataset, resultAttemptSchema } from "./api";

describe("resultAttemptSchema", () => {
  it("accepts legacy result rows without evaluation error metadata", () => {
    const parsed = resultAttemptSchema.parse({
      attempt_id: "attempt-1",
      dataset_id: "dataset-1",
      stream_id: "stream-1",
      external_stream_id: null,
      input_type: "static",
      attempt_index: 0,
      source_prompt: "prompt",
      source_output: "output",
      source_verdict: "THREAT",
      judge_verdict: "SAFE",
      comparison_status: "SOURCE_STRICTER_THAN_JUDGE",
      review_decision: null,
      reviewer_identity: null,
      reviewed_at: null,
      severity: null,
      category: null,
      technique: null,
      created_at: "2026-06-04T00:00:00Z",
    });

    expect(parsed.evaluation_error_code).toBeNull();
    expect(parsed.evaluation_error_message).toBeNull();
    expect(parsed.evaluation_error_created_at).toBeNull();
  });
});

describe("evaluationJobSchema", () => {
  it("accepts safe evaluation progress metadata", () => {
    const parsed = evaluationJobSchema.parse({
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
      status: "RUNNING",
      retry_limit: 2,
      total_attempts: 10,
      processed_attempts: 4,
      succeeded_attempts: 3,
      failed_attempts: 1,
      created_at: "2026-06-04T00:00:00Z",
      updated_at: "2026-06-04T00:01:00Z",
      started_at: "2026-06-04T00:00:10Z",
      completed_at: null,
    });

    expect(parsed.status).toBe("RUNNING");
    expect(parsed.processed_attempts).toBe(4);
    expect(parsed.succeeded_attempts).toBe(3);
    expect(parsed.failed_attempts).toBe(1);
  });
});

describe("importDataset", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("posts the selected file without converting it to text", async () => {
    const file = new File(
      ['[{"prompt":"p","output":"o","threat":false}]'],
      "attacks.json",
      {
        type: "application/json",
      },
    );
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          dataset_id: "dataset-1",
          project_id: "project-1",
          scan_name: "attacks.json",
          detected_format: "static_json",
          stream_count: 1,
          attempt_count: 1,
          imported_count: 1,
          error_count: 0,
          status: "imported",
        }),
        {
          headers: { "Content-Type": "application/json" },
          status: 201,
        },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await importDataset({ file });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/datasets/import?filename=attacks.json",
      expect.objectContaining({
        body: file,
        method: "POST",
      }),
    );
  });
});
