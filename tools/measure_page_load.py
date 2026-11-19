"""Local fresh-context navigation timings; remote requests are blocked."""
import argparse,json,sys
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools.benchmark_local import summary

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--base',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
    if urlparse(args.base).hostname not in ('127.0.0.1','localhost','::1'):raise ValueError('Loopback only')
    navigation=[];bytes_=[];requests_=[];errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch()
        for _ in range(24):
            context=browser.new_context(viewport={'width':390,'height':844});page=context.new_page()
            page.route('**/*',lambda route:route.continue_() if urlparse(route.request.url).hostname in ('127.0.0.1','localhost','::1') else route.abort())
            page.on('pageerror',lambda error:errors.append(str(error)));page.goto(args.base,wait_until='load');page.wait_for_timeout(100)
            data=page.evaluate("()=>({ms:performance.getEntriesByType('navigation')[0].domContentLoadedEventEnd,bytes:performance.getEntriesByType('resource').reduce((sum,r)=>sum+r.transferSize,0),requests:performance.getEntriesByType('resource').length})")
            navigation.append(data['ms']);bytes_.append(data['bytes']);requests_.append(data['requests']);context.close()
        browser.close()
    result={'navigation_dom_content_loaded_ms':summary(navigation),'subresource_transfer_bytes':summary(bytes_),'subresource_requests':summary(requests_),'browser_errors':errors,'scope':'24 fresh Chromium contexts, mobile viewport, loopback, external requests blocked; not WAN or phone timing'}
    Path(args.output).write_text(json.dumps(result,indent=2));print(json.dumps(result))
