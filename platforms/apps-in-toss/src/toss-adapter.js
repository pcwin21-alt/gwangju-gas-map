import { Device, Accuracy, User } from '@apps-in-toss/web-framework';
import { createLocationBridge } from './location-bridge.js';

window.GasToss = createLocationBridge(Device.getLocation, Accuracy.High);
// Do not send this key to the legacy reporting/analytics services.
Promise.resolve().then(() => User.getAnonymousKey()).then(result => {
  if (result?.type === 'HASH' && result.hash) {
    try { localStorage.setItem('onnuri-toss-user', result.hash); } catch (_) { /* Map remains usable with blocked storage. */ }
  }
}).catch(() => { /* Old clients or a browser preview must retain manual browsing. */ });
