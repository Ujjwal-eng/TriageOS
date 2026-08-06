const GOOGLE_CLIENT_ID = "153149870402-gtvkkkjeupoat9rjhj1o0nkrejh2of7p.apps.googleusercontent.com";
 
function decodeJwtPayload(token) {
  // Just base64-decodes the middle segment of the JWT. No signature
  // check — see the honest note above for why that's fine here and
  // would NOT be fine for anything handling real access control.
  const payload = token.split('.')[1];
  const json = atob(payload.replace(/-/g, '+').replace(/_/g, '/'));
  return JSON.parse(json);
}
 
function handleGoogleCredential(response) {
  const profile = decodeJwtPayload(response.credential);
  sessionStorage.setItem('triageos_user', JSON.stringify({
    name: profile.name,
    email: profile.email,
  }));
  window.location.href = '/console.html';
}
 
// Exposed globally and called by the <script onload="..."> in index.html
// — this GUARANTEES Google's library has actually finished loading
// before we ever touch `google.accounts`, instead of guessing based on
// whatever order scripts happen to finish in.
window.initGoogleSignIn = function () {
  if (GOOGLE_CLIENT_ID.startsWith('YOUR_GOOGLE_CLIENT_ID')) {
    console.warn(
      'TriageOS: Google Sign-In is not configured yet. Add your real ' +
      'Client ID in static/login.js. "Continue without signing in" still works.'
    );
    return;
  }
  google.accounts.id.initialize({
    client_id: GOOGLE_CLIENT_ID,
    callback: handleGoogleCredential,
  });
  google.accounts.id.renderButton(
    document.getElementById('google-signin-button'),
    { theme: 'outline', size: 'large', shape: 'pill', width: 280 }
  );
};
 
