import { describe, expect, it } from "vitest";

import { resultAttemptSchema } from "./api";

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
