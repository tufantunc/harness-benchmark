export interface TaskRun {
  id: number;
  run_id: string;
  harness: string;
  model: string;
  language: string;
  exercise: string;
  repetition: number;
  success: number;
  tokens_input: number;
  tokens_output: number;
  tokens_cached: number;
  cost_usd: number;
  duration_sec: number;
  tool_calls: number;
  llm_calls: number;
  diff_loc: number;
  timed_out: number;
  tampered: number;
  artifact_path: string;
  created_at: string;
  cache_write_tokens: number;
  cache_read_tokens: number;
  system_prompt_tokens: number;
  tool_schema_tokens: number;
  prefix_stable: number;
  request_count: number;
}

export interface HarnessSummary {
  harness: string;
  total_tasks: number;
  success_count: number;
  success_rate: number;
  pass_at_k: number;
  avg_tokens_in: number;
  avg_tokens_out: number;
  avg_llm_calls: number;
  avg_tool_calls: number | null;
  avg_duration: number;
  avg_system_prompt: number;
  avg_tool_schemas: number;
  avg_requests: number;
  prefix_stable_rate: number;
}

export interface BenchmarkData {
  runs: TaskRun[];
  generated_at: string;
}
