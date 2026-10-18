// Fail closed: browser requests can reach only this smoke run's owned servers.
export function browserRoute(value, config) {
  const url=new URL(value);
  if(url.origin===config.ui||url.origin===config.api)return {action:'continue'};
  if(['http:','https:'].includes(url.protocol)&&url.pathname.startsWith('/api/v1/')){
    return {action:'redirect',url:config.api+url.pathname};
  }
  return {action:'block'};
}
