// Reproducible native integration for the pinned react-native-webview version.
// Fail on upstream changes rather than silently shipping without filtering.
const fs=require('node:fs');const path=require('node:path');const crypto=require('node:crypto');
const {DOMAINS,appleRules}=require('../blocker.cjs');
const UA='AfterglowBlock/1';
function removeSection(source,name){return source.replace(new RegExp('\\n[ \\t]*// AFTERGLOW_'+name+'_START[\\s\\S]*?// AFTERGLOW_'+name+'_END\\n','g'),'')}
function patchAndroid(source){
 source=removeSection(removeSection(source,'FILTER'),'UA');
 if(source.includes('shouldInterceptRequest('))throw Error('Upstream WebView already intercepts resources. Review the ad-block integration before upgrading.');
 const anchor='public class RNCWebViewClient extends WebViewClient {';
 if(!source.includes(anchor)||!source.includes('super.onPageStarted(webView, url, favicon);'))throw Error('Android WebView source changed. Review the ad-block integration.');
 const code=`
    // AFTERGLOW_FILTER_START
    private volatile boolean afterglowBlocking = false;
    private static final String[] AFTERGLOW_DOMAINS = {${DOMAINS.map(domain=>JSON.stringify(domain)).join(', ')}};
    private static boolean afterglowShouldBlock(String value) {
        try {
            android.net.Uri uri = android.net.Uri.parse(value);
            String scheme = uri.getScheme();
            if (!("http".equals(scheme) || "https".equals(scheme))) return false;
            String host = uri.getHost();
            if (host == null) return false;
            host = host.toLowerCase(java.util.Locale.ROOT);
            for (String domain : AFTERGLOW_DOMAINS) if (host.equals(domain) || host.endsWith("." + domain)) return true;
            String route = uri.getPath();
            return (host.equals("youtube.com") || host.endsWith(".youtube.com")) && route != null && (route.startsWith("/pagead/") || route.equals("/api/stats/ads") || route.startsWith("/api/stats/ads/"));
        } catch (Exception ignored) { return false; }
    }
    @Override
    public WebResourceResponse shouldInterceptRequest(WebView view, WebResourceRequest request) {
        if (afterglowBlocking && !request.isForMainFrame() && afterglowShouldBlock(request.getUrl().toString())) {
            return new WebResourceResponse("text/plain", "UTF-8", 204, "No Content", java.util.Collections.emptyMap(), new java.io.ByteArrayInputStream(new byte[0]));
        }
        return super.shouldInterceptRequest(view, request);
    }
    // AFTERGLOW_FILTER_END
`;
 source=source.replace(anchor,anchor+code);
 source=source.replace('super.onPageStarted(webView, url, favicon);',`super.onPageStarted(webView, url, favicon);
      // AFTERGLOW_UA_START
      afterglowBlocking = webView.getSettings().getUserAgentString().contains("${UA}");
      // AFTERGLOW_UA_END
`);
 return source;
}
function patchApple(source){
 source=removeSection(source,'FILTER');
 const anchor='_webView = [[RNCWKWebView alloc] initWithFrame:self.bounds configuration: wkWebViewConfig];';
 if(!source.includes(anchor))throw Error('Apple WebView source changed. Review the ad-block integration.');
 const rules=JSON.stringify(appleRules()),identifier='afterglow-'+crypto.createHash('sha256').update(rules).digest('hex').slice(0,16);
 const literal=JSON.stringify(rules);
 return source.replace(anchor,anchor+`
    // AFTERGLOW_FILTER_START
    if (@available(iOS 11.0, macOS 10.13, *)) {
      if ([wkWebViewConfig.applicationNameForUserAgent containsString:@"${UA}"]) {
        __weak WKWebView *afterglowView = _webView;
        [[WKContentRuleListStore defaultStore] compileContentRuleListForIdentifier:@"${identifier}"
          encodedContentRuleList:@${literal}
          completionHandler:^(WKContentRuleList *ruleList, NSError *error) {
            dispatch_async(dispatch_get_main_queue(), ^{
              WKWebView *currentView = afterglowView;
              if (ruleList && currentView) [currentView.configuration.userContentController addContentRuleList:ruleList];
              if (error) NSLog(@"Afterglow ad filtering could not start: %@", error.localizedDescription);
            });
          }];
      }
    }
    // AFTERGLOW_FILTER_END
`);
}
function install(){
 const root=path.dirname(require.resolve('react-native-webview/package.json'));
 const version=JSON.parse(fs.readFileSync(path.join(root,'package.json'),'utf8')).version;
 if(version!=='14.0.1')throw Error('Ad-block integration requires react-native-webview 14.0.1. Review native source before changing versions.');
 const android=path.join(root,'android/src/main/java/com/reactnativecommunity/webview/RNCWebViewClient.java');
 const apple=path.join(root,'apple/RNCWebViewImpl.m');
 const a=patchAndroid(fs.readFileSync(android,'utf8')),i=patchApple(fs.readFileSync(apple,'utf8'));
 fs.writeFileSync(android,a);fs.writeFileSync(apple,i);
 console.log('Installed Afterglow native ad/tracker filters for Android and iPhone standalone builds.');
}
if(require.main===module)install();
module.exports={patchAndroid,patchApple};
