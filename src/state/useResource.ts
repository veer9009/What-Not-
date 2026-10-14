import { useCallback, useEffect, useRef, useState } from 'react';
import { errorMessage } from '../api/client';
export function useResource<T>(loader: () => Promise<T>) {
  const [data,setData]=useState<T|null>(null); const [error,setError]=useState(''); const [loading,setLoading]=useState(true);
  const version=useRef(0); const mounted=useRef(true); const currentLoader=useRef(loader);
  currentLoader.current=loader;
  const reload=useCallback(async()=>{
    const active=()=>mounted.current&&currentLoader.current===loader;
    if(!active())return false;
    const ticket=++version.current;setLoading(true);setError('');
    try {
      const result=await loader();
      if(!active()||ticket!==version.current)return false;
      setData(result);setLoading(false);return true;
    } catch(reason) {
      if(!active()||ticket!==version.current)return false;
      setError(errorMessage(reason));setData(null);setLoading(false);return false;
    }
  },[loader]);
  useEffect(()=>{mounted.current=true;void reload();return()=>{mounted.current=false;version.current++;};},[reload]);
  return {data,error,loading,reload};
}
