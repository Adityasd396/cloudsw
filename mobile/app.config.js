module.exports = ({config}) => {
  const release=process.env.AFTERGLOW_RELEASE==='1';
  const server=process.env.EXPO_PUBLIC_API_URL||'';
  if(release&&server&&!server.startsWith('https://'))throw new Error('Standalone release builds require an HTTPS backend URL, or leave the URL empty for users to enter it.');
  return {
    ...config,
    android:{...config.android,usesCleartextTraffic:!release},
    ios:{...config.ios,infoPlist:{...config.ios?.infoPlist,NSAppTransportSecurity:release?{}:{NSAllowsLocalNetworking:true}}}
  };
};
