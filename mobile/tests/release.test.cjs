const test=require('node:test');
const assert=require('node:assert/strict');
const configure=require('../app.config.js');
const base=require('../app.json').expo;
test('standalone release requires HTTPS when preconfigured and disables cleartext',()=>{
 const originalRelease=process.env.AFTERGLOW_RELEASE,originalUrl=process.env.EXPO_PUBLIC_API_URL;
 try{
  process.env.AFTERGLOW_RELEASE='1';delete process.env.EXPO_PUBLIC_API_URL;
  const release=configure({config:base});
  assert.equal(release.android.usesCleartextTraffic,false);
  assert.deepEqual(release.ios.infoPlist.NSAppTransportSecurity,{});
  process.env.EXPO_PUBLIC_API_URL='http://example.test';
  assert.throws(()=>configure({config:base}),/HTTPS/);
  process.env.EXPO_PUBLIC_API_URL='https://example.test';
  assert.equal(configure({config:base}).android.usesCleartextTraffic,false);
 }finally{
  if(originalRelease===undefined)delete process.env.AFTERGLOW_RELEASE;else process.env.AFTERGLOW_RELEASE=originalRelease;
  if(originalUrl===undefined)delete process.env.EXPO_PUBLIC_API_URL;else process.env.EXPO_PUBLIC_API_URL=originalUrl;
 }
});
