let emailToken=new URLSearchParams(location.hash.slice(1)).get('token')||'';
if(location.hash)history.replaceState(null,'',location.pathname);
const reset=document.getElementById('passwordReset'),requestForm=document.getElementById('recoveryRequest');
if(reset){reset.hidden=!emailToken;requestForm.hidden=!!emailToken}
form('recoveryRequest',async fields=>{const result=await accountRequest('/api/auth/recovery',{email:fields.get('email')});tell(result.message)});
form('passwordReset',async fields=>{const result=await accountRequest('/api/auth/reset',{token:emailToken,password:fields.get('password')});emailToken='';reset.hidden=true;tell(result.message);window.ReactNativeWebView?.postMessage(JSON.stringify({type:'account-identity-changed'}))});
form('emailVerification',async()=>{const result=await accountRequest('/api/auth/verify',{token:emailToken});emailToken='';document.getElementById('emailVerification').hidden=true;tell(result.message)});
if(document.getElementById('emailVerification')&&!emailToken){document.getElementById('emailVerification').hidden=true;tell('Open the one-use link from your verification email, or request a new one from your account.')}
