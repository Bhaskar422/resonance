import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import '../styles.css';
import { Logo } from '../components/ui.jsx';
import { Footer } from './Site.jsx';

// The privacy policy (/privacy) and terms of service (/terms). Google's consent screen links
// to both, and the site's footer and the sign-in page link here too.

const UPDATED = 'November 4, 2026';
const ISSUES = 'https://github.com/Bhaskar422/resonance/issues';
const WRAP = 'max-w-[760px] mx-auto';

try { document.documentElement.dataset.theme = JSON.parse(localStorage.getItem('resonance:A:theme')) || 'dark'; } catch (e) { document.documentElement.dataset.theme = 'dark'; }

const H2 = ({ children }) => <h2 className="mt-10 mb-3 text-[20px] font-semibold tracking-[-.01em]">{children}</h2>;
const P = ({ children }) => <p className="my-3 text-fg-2 leading-[1.65]">{children}</p>;
const UL = ({ children }) => <ul className="my-3 pl-5 flex flex-col gap-2 text-fg-2 leading-[1.6]">{children}</ul>;
const A = ({ href, children }) => <a href={href} className="text-accent">{children}</a>;

function Privacy() {
  return (
    <>
      <P>Resonance is an open-source tool (Apache-2.0) that measures machine vibration from slow-motion video. This policy explains what it stores about you, why, who else sees it, and how to delete it.</P>

      <H2>What we collect</H2>
      <UL>
        <li><b className="text-fg">Your account.</b> Your email address, name and profile picture. If you sign up with an email and password, the password is stored only as a salted scrypt hash, never in plain text.</li>
        <li><b className="text-fg">Sign in with Google.</b> Google shares your Google account ID, email address, whether the email is verified, your name and your profile picture (the <code>openid</code>, <code>email</code> and <code>profile</code> scopes). We do not ask for access to Gmail, Drive, contacts or anything else.</li>
        <li><b className="text-fg">Sign in with GitHub.</b> GitHub shares your user ID, username, name, avatar and verified email addresses (read-only <code>read:user</code> and <code>user:email</code>). We do not ask for access to your repositories.</li>
        <li><b className="text-fg">Sign-in records.</b> Browser sessions and access tokens for the command-line tool and the iPhone app. They are stored as hashes, with the time each token was last used.</li>
        <li><b className="text-fg">What you upload.</b> Videos (including their soundtrack), accelerometer recordings, equipment manuals, and the part and machine names you type, plus the results Resonance computes from them.</li>
      </UL>
      <P>Resonance has no analytics, advertising or tracking scripts. Your browser keeps a few preferences (theme, chosen tabs) in local storage. Pages load their fonts from Google Fonts, which receives your IP address like any web request.</P>

      <H2>How we use it</H2>
      <UL>
        <li>To sign you in and show your name and picture in the app.</li>
        <li>To keep your runs private to your account.</li>
        <li>To analyse what you upload and show you the results.</li>
      </UL>
      <P>We do not sell your data, use it for advertising, or share it with anyone except as described below. Your Google or GitHub profile is never sent to an AI model.</P>

      <H2>Who else processes your uploads</H2>
      <P>The analysis uses Meta's models through the Meta Model API. When you analyse a clip, these are sent to Meta: your video or frames from it (to find the machine part with SAM 3.1); the measured numbers, the original and magnified video, the spectrum chart, a key frame, up to 20 seconds of the soundtrack and the manual you attach (to diagnose with Muse Spark); the key frame again (to draw the fix with Muse Image); and, when you rescan, the before-and-after measurements (to judge the fix). Meta's own terms and privacy policy govern how Meta handles them.</P>

      <H2>How long we keep it, and deleting it</H2>
      <P>We keep your account and runs until you delete them. In the workspace, open <b className="text-fg">Settings → Delete account</b>. This erases your account, its Google and GitHub links, sessions and access tokens, every run you created, and the videos and files you uploaded for them. We keep an API cost log (model, token counts, price and run ID) to account for spending; it contains none of your content. Copies already sent to Meta are subject to Meta's retention rules.</P>
      <P>You can also remove Resonance's access at any time: in your <A href="https://myaccount.google.com/connections">Google account connections</A>, or in <A href="https://github.com/settings/applications">GitHub → Settings → Applications</A>.</P>

      <H2>Google user data</H2>
      <P>Resonance's use and transfer of information received from Google APIs adheres to the <A href="https://developers.google.com/terms/api-services-user-data-policy">Google API Services User Data Policy</A>, including the Limited Use requirements. Google user data is used only to sign you in and identify your account. It is not transferred to others, used for advertising, or used to train AI models.</P>

      <H2>Security</H2>
      <P>Passwords, session cookies and access tokens are stored only as hashes. Session cookies are HttpOnly. Repeated failed sign-ins are rate-limited. No system is perfectly secure; tell us at once if you find a problem.</P>

      <H2>Children</H2>
      <P>Resonance is not directed at children under 13, and we do not knowingly collect their data.</P>

      <H2>If you run Resonance yourself</H2>
      <P>Resonance is open source. If you host your own copy, your data stays on your server and the Meta API calls go out under your own API key. This policy then describes the software, and you are the operator responsible for your users' data.</P>

      <H2>Changes and contact</H2>
      <P>If this policy changes, we will update this page and its date. For questions or deletion requests, open an issue at <A href={ISSUES}>{ISSUES.replace('https://', '')}</A>.</P>
    </>
  );
}

function Terms() {
  return (
    <>
      <P>By creating an account or using Resonance, you agree to these terms.</P>

      <H2>The service</H2>
      <P>Resonance measures vibration from slow-motion video and uses AI models to suggest what may be wrong with a machine. It is open-source software (Apache-2.0) offered free of charge. Features may change, and the hosted service may be limited, paused or stopped at any time.</P>

      <H2>Not a substitute for an expert</H2>
      <P>Diagnoses, fix suggestions and images are generated by AI and can be wrong. They are not professional engineering advice or a safety certification. Before touching a machine, switch it off and secure it so it cannot start, and follow its manual and your workplace's safety rules. A qualified technician should confirm any fault and repair.</P>

      <H2>Your content</H2>
      <UL>
        <li>You keep ownership of what you upload. You allow Resonance to store and process it to provide the service, including sending it to Meta's models as described in the <A href="/privacy">privacy policy</A>.</li>
        <li>Only upload content you have the right to share. Avoid filming people, or anything confidential you are not allowed to share.</li>
        <li>You can delete your account and content at any time in Settings.</li>
      </UL>

      <H2>Your account</H2>
      <UL>
        <li>Give a real email address, keep your password and access tokens secret, and revoke tokens you no longer use.</li>
        <li>Do not misuse the service: no automated sign-ups, no attempts to reach other users' data, no overloading it, and no content that is illegal or infringes others' rights.</li>
        <li>Analysis uses paid API calls. We may limit usage, or suspend accounts that break these terms.</li>
      </UL>

      <H2>No warranty, limited liability</H2>
      <P>Resonance is provided "as is", without warranties of any kind, as set out in the Apache-2.0 license. To the extent the law allows, its developer is not liable for any damage, loss or injury arising from using the service or acting on its results.</P>

      <H2>Changes and contact</H2>
      <P>If these terms change, we will update this page and its date. Questions: <A href={ISSUES}>{ISSUES.replace('https://', '')}</A>.</P>
    </>
  );
}

function Legal() {
  const terms = location.pathname.replace(/\/+$/, '').endsWith('/terms');
  return (
    <>
      <header className="border-b border-line">
        <div className="max-w-[1240px] mx-auto flex items-center gap-4 px-4 py-3 desk:px-6">
          <Logo href="/" />
          <nav className="ml-auto flex gap-[18px] font-mono text-[12px] font-medium tracking-[.06em]">
            <a href="/privacy" className={terms ? 'text-fg-2' : 'text-fg'}>PRIVACY</a>
            <a href="/terms" className={terms ? 'text-fg' : 'text-fg-2'}>TERMS</a>
            <a href="/app" className="text-fg-2">WORKSPACE</a>
          </nav>
        </div>
      </header>
      <main className={`${WRAP} px-4 desk:px-6 pt-12 pb-20`}>
        <div className="font-mono text-[11.5px] font-medium tracking-[.16em] text-signal">LAST UPDATED {UPDATED.toUpperCase()}</div>
        <h1 className="mt-3 mb-6 text-[length:clamp(32px,5vw,44px)] tracking-[-.025em] font-semibold">{terms ? 'Terms of Service' : 'Privacy Policy'}</h1>
        {terms ? <Terms /> : <Privacy />}
      </main>
      <Footer />
    </>
  );
}

createRoot(document.getElementById('root')).render(<StrictMode><Legal /></StrictMode>);
