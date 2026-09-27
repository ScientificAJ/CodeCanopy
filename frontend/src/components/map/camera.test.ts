import { afterEach, expect, it } from 'vitest'
import { readCamera, saveCamera, validCamera } from './camera'
afterEach(() => sessionStorage.clear())
it('persists independent cameras and rejects corrupt or excessive state', () => {
  saveCamera('codecanopy-camera:one',{x:200,y:300,scale:1.5})
  saveCamera('codecanopy-camera:two',{x:50,y:60,scale:2})
  expect(readCamera('codecanopy-camera:one')).toEqual({x:200,y:300,scale:1.5})
  expect(readCamera('codecanopy-camera:two')?.scale).toBe(2)
  sessionStorage.setItem('bad','{"x":0,"y":0,"scale":99}')
  expect(readCamera('bad')).toBeUndefined()
  expect(validCamera({x:Infinity,y:1,scale:1})).toBe(false)
  expect(validCamera({x:'1',y:1,scale:1})).toBe(false)
})
it('bounds saved camera history without removing unrelated browser state', () => {
  sessionStorage.setItem('unrelated','preserved')
  for(let i=0;i<100;i++) saveCamera('codecanopy-camera:'+i,{x:0,y:0,scale:1})
  expect(Object.keys(sessionStorage).filter(k=>k.startsWith('codecanopy-camera:'))).toHaveLength(80)
  expect(sessionStorage.getItem('unrelated')).toBe('preserved')
})
