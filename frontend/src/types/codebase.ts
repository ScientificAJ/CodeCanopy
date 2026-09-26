export interface Function {
  name: string
  file: string
  line_start: number
  line_end: number
}

export interface Class {
  name: string
  file: string
  line_start: number
  line_end: number
}

export interface File {
  path: string
  name: string
  language: string
  size: number
  functions: Function[]
  classes: Class[]
  imports: string[]
}

export interface Project {
  id: string
  name: string
  files: File[]
}

export interface Relationship {
  source: string
  target: string
  type: string
}

export interface ReusableGroup {
  function_name: string
  defined_in: string
  defined_line_start: number
  defined_line_end: number
  called_from: string[]
}

export interface ReusableFunctionResult {
  snapshot_id: string
  groups: ReusableGroup[]
  total_reusable: number
}
