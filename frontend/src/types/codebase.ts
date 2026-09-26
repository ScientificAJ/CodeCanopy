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