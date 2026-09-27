export interface SourceCitation { id: string; file_id: string; path: string; line_start: number; line_end: number }
export interface AskResponse { answer: string; context_hint: string; sources: SourceCitation[]; limitations: string[] }
