/* @ds-bundle: {"format":4,"namespace":"ElevionixDesignSystem_f5b95d","components":[{"name":"Wordmark","sourcePath":"components/brand/Wordmark.jsx"},{"name":"Button","sourcePath":"components/buttons/Button.jsx"},{"name":"Badge","sourcePath":"components/feedback/Badge.jsx"},{"name":"EmptyState","sourcePath":"components/feedback/EmptyState.jsx"},{"name":"Field","sourcePath":"components/forms/Field.jsx"},{"name":"Panel","sourcePath":"components/surfaces/Panel.jsx"},{"name":"StatCard","sourcePath":"components/surfaces/StatCard.jsx"},{"name":"Eyebrow","sourcePath":"components/typography/Eyebrow.jsx"},{"name":"SealHeading","sourcePath":"components/typography/SealHeading.jsx"}],"sourceHashes":{"components/brand/Wordmark.jsx":"c8724fac80e3","components/buttons/Button.jsx":"0728375db55e","components/feedback/Badge.jsx":"c356efae1b35","components/feedback/EmptyState.jsx":"e3a9b3efe358","components/forms/Field.jsx":"290758bdcb76","components/surfaces/Panel.jsx":"13cb12baac56","components/surfaces/StatCard.jsx":"be5af3dae899","components/typography/Eyebrow.jsx":"71c1ec808b58","components/typography/SealHeading.jsx":"e54e31a42642","ui_kits/elevionix-app/App.jsx":"20558267e488","ui_kits/elevionix-app/AppShell.jsx":"0fa954bf4aa6","ui_kits/elevionix-app/ApprovalsScreen.jsx":"0bcb5d9a2edd","ui_kits/elevionix-app/MattersScreen.jsx":"346df7ac42ab","ui_kits/elevionix-app/PlaceholderScreens.jsx":"7d932f13db12","ui_kits/elevionix-app/WorkflowsScreen.jsx":"0b7d6c60bbdf","ui_kits/elevionix-app/data.js":"81615d8749c7"},"inlinedExternals":[],"unexposedExports":[]} */

(() => {

const __ds_ns = (window.ElevionixDesignSystem_f5b95d = window.ElevionixDesignSystem_f5b95d || {});

const __ds_scope = {};

(__ds_ns.__errors = __ds_ns.__errors || []);

// components/brand/Wordmark.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Elevionix Wordmark — the type lockup. Italic heavy display "ELEVIONIX" with a mono "TECH LABS" tagline.
 * on="light" for brown text on cream; on="dark" for cream text on the brown anchor.
 * compact drops the tagline and shrinks (for app bars). The PNG logo lives in assets/elevionix-logo.png.
 */
function Wordmark({
  on = 'light',
  compact = false,
  tagline = 'Tech Labs',
  style,
  ...rest
}) {
  const name = on === 'dark' ? 'var(--yellow-pale)' : 'var(--brown)';
  const tag = on === 'dark' ? 'var(--yellow)' : 'var(--gold)';
  if (compact) {
    return /*#__PURE__*/React.createElement("span", _extends({
      style: {
        fontFamily: 'var(--font-display)',
        fontWeight: 800,
        fontStyle: 'italic',
        fontSize: '14px',
        letterSpacing: '.06em',
        textTransform: 'uppercase',
        color: name,
        ...style
      }
    }, rest), "Elevionix", /*#__PURE__*/React.createElement("span", {
      style: {
        color: 'var(--orange)'
      }
    }, "."));
  }
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      display: 'inline-block',
      lineHeight: 1,
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-display)',
      fontWeight: 800,
      fontStyle: 'italic',
      fontSize: '21px',
      letterSpacing: '.06em',
      textTransform: 'uppercase',
      color: name
    }
  }, "Elevionix"), tagline && /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-data)',
      fontWeight: 500,
      fontSize: '9.5px',
      letterSpacing: '.42em',
      textTransform: 'uppercase',
      color: tag,
      marginTop: '2px'
    }
  }, tagline));
}
Object.assign(__ds_scope, { Wordmark });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/brand/Wordmark.jsx", error: String((e && e.message) || e) }); }

// components/buttons/Button.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Elevionix Button.
 * Orange (accent) commits. Deep brown (primary) is neutral-primary. Quiet is reversible.
 */
function Button({
  variant = 'accent',
  size = 'md',
  disabled = false,
  type = 'button',
  onClick,
  children,
  style,
  ...rest
}) {
  const sizes = {
    sm: {
      padding: '7px 14px',
      fontSize: '13px'
    },
    md: {
      padding: '10px 18px',
      fontSize: '14px'
    },
    lg: {
      padding: '13px 24px',
      fontSize: '15px'
    }
  };
  const variants = {
    accent: {
      background: 'var(--orange)',
      color: '#fff',
      borderColor: 'transparent'
    },
    primary: {
      background: 'var(--brown-deep)',
      color: 'var(--yellow-pale)',
      borderColor: 'transparent'
    },
    quiet: {
      background: 'transparent',
      color: 'var(--brown)',
      borderColor: 'var(--gold-soft)'
    }
  };
  const base = {
    fontFamily: 'var(--font-text)',
    fontWeight: 600,
    lineHeight: 1,
    borderRadius: 'var(--r-sm)',
    border: '1px solid',
    cursor: disabled ? 'not-allowed' : 'pointer',
    opacity: disabled ? 0.5 : 1,
    transition: 'background .15s, border-color .15s',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '8px',
    ...sizes[size],
    ...variants[variant],
    ...style
  };
  return /*#__PURE__*/React.createElement("button", _extends({
    type: type,
    disabled: disabled,
    onClick: onClick,
    style: base
  }, rest), children);
}
Object.assign(__ds_scope, { Button });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/buttons/Button.jsx", error: String((e && e.message) || e) }); }

// components/feedback/Badge.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Elevionix status Badge. State is always written out, never colour-only.
 * active fills yellow · pending leans orange · draft is a quiet outline.
 */
function Badge({
  variant = 'active',
  children,
  style,
  ...rest
}) {
  const variants = {
    active: {
      color: 'var(--status-active-fg)',
      background: 'var(--status-active-bg)',
      borderColor: 'var(--status-active-border)'
    },
    pending: {
      color: 'var(--status-pending-fg)',
      background: 'var(--status-pending-bg)',
      borderColor: 'var(--status-pending-border)'
    },
    draft: {
      color: 'var(--status-draft-fg)',
      background: 'var(--status-draft-bg)',
      borderColor: 'var(--status-draft-border)'
    }
  };
  const base = {
    display: 'inline-block',
    fontFamily: 'var(--font-data)',
    fontSize: '11px',
    letterSpacing: '.06em',
    padding: '3px 10px',
    borderRadius: 'var(--r-pill)',
    border: '1px solid',
    whiteSpace: 'nowrap',
    ...variants[variant],
    ...style
  };
  return /*#__PURE__*/React.createElement("span", _extends({
    style: base
  }, rest), children);
}
Object.assign(__ds_scope, { Badge });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/Badge.jsx", error: String((e && e.message) || e) }); }

// components/feedback/EmptyState.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Elevionix EmptyState. Quiet heading, one line of guidance, one accent action.
 */
function EmptyState({
  title,
  description,
  actionLabel,
  onAction,
  style,
  ...rest
}) {
  const wrap = {
    fontFamily: 'var(--font-text)',
    color: 'var(--brown)',
    ...style
  };
  return /*#__PURE__*/React.createElement("div", _extends({
    style: wrap
  }, rest), title && /*#__PURE__*/React.createElement("h3", {
    style: {
      fontFamily: 'var(--font-display)',
      fontWeight: 700,
      fontSize: '17px',
      margin: '0 0 6px',
      letterSpacing: '-.015em'
    }
  }, title), description && /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: '13px',
      lineHeight: 1.45,
      color: 'var(--brown-mid)',
      margin: '0 0 14px',
      maxWidth: '46ch'
    }
  }, description), actionLabel && /*#__PURE__*/React.createElement(__ds_scope.Button, {
    variant: "accent",
    onClick: onAction
  }, actionLabel));
}
Object.assign(__ds_scope, { EmptyState });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/feedback/EmptyState.jsx", error: String((e && e.message) || e) }); }

// components/forms/Field.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Elevionix form Field: uppercase mono label, input, optional hint.
 */
function Field({
  label,
  hint,
  id,
  value,
  defaultValue,
  placeholder,
  onChange,
  type = 'text',
  style,
  ...rest
}) {
  const fieldId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);
  const [focus, setFocus] = React.useState(false);
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      fontFamily: 'var(--font-text)',
      ...style
    }
  }, rest), label && /*#__PURE__*/React.createElement("label", {
    htmlFor: fieldId,
    style: {
      display: 'block',
      fontFamily: 'var(--font-data)',
      fontSize: '11px',
      letterSpacing: '.1em',
      textTransform: 'uppercase',
      color: 'var(--brown-mid)',
      marginBottom: '6px'
    }
  }, label), /*#__PURE__*/React.createElement("input", {
    id: fieldId,
    type: type,
    value: value,
    defaultValue: defaultValue,
    placeholder: placeholder,
    onChange: onChange,
    onFocus: () => setFocus(true),
    onBlur: () => setFocus(false),
    style: {
      width: '100%',
      padding: '10px 12px',
      fontFamily: 'var(--font-text)',
      fontSize: '15px',
      color: 'var(--brown)',
      background: '#fff',
      border: '1px solid ' + (focus ? 'var(--orange)' : 'var(--gold-soft)'),
      borderRadius: 'var(--r-sm)',
      outline: 'none',
      boxShadow: focus ? 'var(--focus-ring)' : 'none',
      boxSizing: 'border-box'
    }
  }), hint && /*#__PURE__*/React.createElement("p", {
    style: {
      fontSize: '12px',
      color: 'var(--brown-mid)',
      margin: '6px 0 0'
    }
  }, hint));
}
Object.assign(__ds_scope, { Field });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/forms/Field.jsx", error: String((e && e.message) || e) }); }

// components/surfaces/Panel.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Elevionix Panel — the standard raised card: cream surface, gold-soft hairline, 12px radius.
 */
function Panel({
  children,
  style,
  ...rest
}) {
  const base = {
    background: 'var(--yellow-card)',
    border: '1px solid var(--gold-soft)',
    borderRadius: 'var(--r-lg)',
    padding: '22px',
    fontFamily: 'var(--font-text)',
    color: 'var(--brown)',
    ...style
  };
  return /*#__PURE__*/React.createElement("div", _extends({
    style: base
  }, rest), children);
}
Object.assign(__ds_scope, { Panel });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/surfaces/Panel.jsx", error: String((e && e.message) || e) }); }

// components/surfaces/StatCard.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Elevionix StatCard — mono gold label, heavy display value, mono delta.
 * Set warn to render the delta in deep orange (overdue / attention).
 */
function StatCard({
  label,
  value,
  delta,
  warn = false,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("div", _extends({
    style: {
      background: '#fff',
      border: '1px solid var(--gold-soft)',
      borderRadius: 'var(--r-md)',
      padding: '14px',
      fontFamily: 'var(--font-text)',
      ...style
    }
  }, rest), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-data)',
      fontSize: '10px',
      letterSpacing: '.12em',
      textTransform: 'uppercase',
      color: 'var(--gold)'
    }
  }, label), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-display)',
      fontWeight: 800,
      fontSize: '28px',
      letterSpacing: '-.02em',
      marginTop: '6px',
      color: 'var(--brown)'
    }
  }, value), delta && /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-data)',
      fontSize: '12px',
      marginTop: '2px',
      color: warn ? 'var(--orange-deep)' : '#7A5E10'
    }
  }, delta));
}
Object.assign(__ds_scope, { StatCard });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/surfaces/StatCard.jsx", error: String((e && e.message) || e) }); }

// components/typography/Eyebrow.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Elevionix Eyebrow — small uppercase mono gold label, sits above section titles.
 */
function Eyebrow({
  children,
  style,
  ...rest
}) {
  return /*#__PURE__*/React.createElement("p", _extends({
    style: {
      fontFamily: 'var(--font-data)',
      fontSize: '11px',
      letterSpacing: '.16em',
      textTransform: 'uppercase',
      color: 'var(--gold)',
      margin: '0 0 10px',
      ...style
    }
  }, rest), children);
}
Object.assign(__ds_scope, { Eyebrow });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/typography/Eyebrow.jsx", error: String((e && e.message) || e) }); }

// components/typography/SealHeading.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
/**
 * Elevionix SealHeading — a section title stamped with the signature short gold rule ("seal") beneath it.
 */
function SealHeading({
  as = 'h2',
  children,
  style,
  ...rest
}) {
  const Tag = as;
  const sizes = {
    h1: {
      fontSize: 'clamp(38px,6vw,60px)',
      fontWeight: 800,
      lineHeight: 1.04
    },
    h2: {
      fontSize: 'clamp(24px,3.2vw,31px)',
      fontWeight: 700,
      lineHeight: 1.12
    },
    h3: {
      fontSize: '17px',
      fontWeight: 700,
      lineHeight: 1.3
    }
  };
  return /*#__PURE__*/React.createElement(Tag, _extends({
    style: {
      fontFamily: 'var(--font-display)',
      color: 'var(--brown)',
      letterSpacing: '-.015em',
      margin: 0,
      position: 'relative',
      display: 'inline-block',
      paddingBottom: '10px',
      ...sizes[as],
      ...style
    }
  }, rest), children, /*#__PURE__*/React.createElement("span", {
    style: {
      position: 'absolute',
      left: 0,
      bottom: 0,
      height: '4px',
      width: '44px',
      background: 'var(--gold)',
      borderRadius: '2px'
    }
  }));
}
Object.assign(__ds_scope, { SealHeading });
})(); } catch (e) { __ds_ns.__errors.push({ path: "components/typography/SealHeading.jsx", error: String((e && e.message) || e) }); }

// ui_kits/elevionix-app/App.jsx
try { (() => {
// Elevionix app — login → dashboard router. Ties the shell + screens together.
const {
  Wordmark,
  Field,
  Button,
  Eyebrow
} = window.ElevionixDesignSystem_f5b95d;
function LoginScreen({
  onEnter
}) {
  return /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      minHeight: 520,
      border: '1px solid var(--gold-soft)',
      borderRadius: 'var(--r-lg)',
      overflow: 'hidden',
      boxShadow: 'var(--shadow)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      background: 'var(--brown-deep)',
      color: 'var(--yellow-pale)',
      padding: '48px 44px',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between'
    }
  }, /*#__PURE__*/React.createElement(Wordmark, {
    on: "dark"
  }), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("h1", {
    style: {
      fontFamily: 'var(--font-display)',
      fontWeight: 800,
      fontSize: 38,
      lineHeight: 1.04,
      letterSpacing: '-.02em',
      margin: 0,
      color: 'var(--yellow-pale)'
    }
  }, "Automation your business can stand on."), /*#__PURE__*/React.createElement("p", {
    style: {
      fontFamily: 'var(--font-text)',
      fontSize: 16,
      color: '#D9C49A',
      marginTop: 16,
      maxWidth: '34ch'
    }
  }, "Sign in to run your workflows, clear approvals, and keep every matter on schedule."))), /*#__PURE__*/React.createElement("div", {
    style: {
      background: 'var(--yellow-card)',
      padding: '48px 44px',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'center'
    }
  }, /*#__PURE__*/React.createElement(Eyebrow, null, "Sign in"), /*#__PURE__*/React.createElement("h2", {
    style: {
      fontFamily: 'var(--font-display)',
      fontWeight: 700,
      fontSize: 25,
      margin: '0 0 24px',
      color: 'var(--brown)',
      letterSpacing: '-.015em'
    }
  }, "Welcome back"), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      flexDirection: 'column',
      gap: 16
    }
  }, /*#__PURE__*/React.createElement(Field, {
    label: "Work email",
    defaultValue: "priya@elevionix.in"
  }), /*#__PURE__*/React.createElement(Field, {
    label: "Password",
    type: "password",
    defaultValue: "workflow"
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 24
    }
  }, /*#__PURE__*/React.createElement(Button, {
    variant: "accent",
    size: "lg",
    onClick: onEnter,
    style: {
      width: '100%',
      justifyContent: 'center'
    }
  }, "Enter workspace")), /*#__PURE__*/React.createElement("p", {
    style: {
      fontFamily: 'var(--font-data)',
      fontSize: 11,
      letterSpacing: '.06em',
      color: 'var(--brown-mid)',
      marginTop: 16,
      textAlign: 'center'
    }
  }, "Trouble signing in? Contact your admin.")));
}
function App() {
  const [authed, setAuthed] = React.useState(false);
  const [tab, setTab] = React.useState('Workflows');
  const [modal, setModal] = React.useState(false);
  if (!authed) return /*#__PURE__*/React.createElement(LoginScreen, {
    onEnter: () => setAuthed(true)
  });
  const screens = {
    Workflows: /*#__PURE__*/React.createElement(WorkflowsScreen, {
      onNewWorkflow: () => setModal(true)
    }),
    Approvals: /*#__PURE__*/React.createElement(ApprovalsScreen, null),
    Matters: /*#__PURE__*/React.createElement(MattersScreen, null),
    Documents: /*#__PURE__*/React.createElement(DocumentsScreen, null),
    Reports: /*#__PURE__*/React.createElement(ReportsScreen, null)
  };
  return /*#__PURE__*/React.createElement(React.Fragment, null, /*#__PURE__*/React.createElement(AppShell, {
    active: tab,
    onNav: setTab,
    onSignOut: () => setAuthed(false)
  }, screens[tab]), modal && /*#__PURE__*/React.createElement(NewWorkflowModal, {
    onClose: () => setModal(false)
  }));
}
Object.assign(window, {
  App
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/elevionix-app/App.jsx", error: String((e && e.message) || e) }); }

// ui_kits/elevionix-app/AppShell.jsx
try { (() => {
// Elevionix app shell — brown-deep bar, compact wordmark, nav with yellow active underline.
const {
  Wordmark
} = window.ElevionixDesignSystem_f5b95d;
function AppShell({
  active,
  onNav,
  onSignOut,
  children
}) {
  const tabs = ['Workflows', 'Approvals', 'Matters', 'Documents', 'Reports'];
  return /*#__PURE__*/React.createElement("div", {
    style: {
      border: '1px solid var(--gold-soft)',
      borderRadius: 'var(--r-lg)',
      overflow: 'hidden',
      background: 'var(--yellow-card)',
      boxShadow: 'var(--shadow)'
    }
  }, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 16,
      padding: '14px 18px',
      background: 'var(--brown-deep)',
      color: 'var(--yellow-pale)'
    }
  }, /*#__PURE__*/React.createElement(Wordmark, {
    compact: true,
    on: "dark"
  }), /*#__PURE__*/React.createElement("nav", {
    style: {
      display: 'flex',
      gap: 18,
      fontFamily: 'var(--font-text)',
      fontSize: 13
    }
  }, tabs.map(t => {
    const on = t === active;
    return /*#__PURE__*/React.createElement("span", {
      key: t,
      onClick: () => onNav(t),
      style: {
        cursor: 'pointer',
        color: on ? 'var(--yellow-pale)' : '#C4A76B',
        fontWeight: on ? 600 : 400,
        paddingBottom: 2,
        borderBottom: on ? '2px solid var(--yellow)' : '2px solid transparent'
      }
    }, t);
  })), /*#__PURE__*/React.createElement("span", {
    onClick: onSignOut,
    title: "Sign out",
    style: {
      fontFamily: 'var(--font-data)',
      fontSize: 11,
      letterSpacing: '.08em',
      textTransform: 'uppercase',
      color: '#C4A76B',
      cursor: 'pointer'
    }
  }, "Priya S. \xB7\xA0Sign out")), /*#__PURE__*/React.createElement("div", {
    style: {
      padding: '22px 18px'
    }
  }, children));
}
Object.assign(window, {
  AppShell
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/elevionix-app/AppShell.jsx", error: String((e && e.message) || e) }); }

// ui_kits/elevionix-app/ApprovalsScreen.jsx
try { (() => {
// Approvals queue — each row a Panel with amount + approve/decline actions.
const {
  Panel,
  Button,
  Badge,
  Eyebrow,
  SealHeading
} = window.ElevionixDesignSystem_f5b95d;
function ApprovalsScreen() {
  const d = window.ELEVIONIX_DATA;
  const [done, setDone] = React.useState({});
  const rows = d.approvals.filter(a => !done[a.id]);
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement(Eyebrow, null, "Operations"), /*#__PURE__*/React.createElement(SealHeading, {
    as: "h2"
  }, "Pending approvals"), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 20,
      display: 'flex',
      flexDirection: 'column',
      gap: 10
    }
  }, rows.length === 0 && /*#__PURE__*/React.createElement(Panel, null, /*#__PURE__*/React.createElement("p", {
    style: {
      margin: 0,
      color: 'var(--brown-mid)',
      fontSize: 14
    }
  }, "Queue clear \u2014 every request has been actioned.")), rows.map(a => /*#__PURE__*/React.createElement("div", {
    key: a.id,
    style: {
      display: 'grid',
      gridTemplateColumns: '1fr auto auto',
      gap: 16,
      alignItems: 'center',
      background: '#fff',
      border: '1px solid var(--gold-soft)',
      borderRadius: 'var(--r-md)',
      padding: '14px 16px'
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-data)',
      fontSize: 12,
      color: 'var(--brown-mid)'
    }
  }, a.id), /*#__PURE__*/React.createElement("div", {
    style: {
      fontWeight: 600,
      color: 'var(--brown)',
      fontSize: 14,
      marginTop: 2
    }
  }, a.title), /*#__PURE__*/React.createElement("div", {
    style: {
      fontFamily: 'var(--font-data)',
      fontSize: 12,
      color: a.warn ? 'var(--orange-deep)' : 'var(--brown-mid)',
      marginTop: 2
    }
  }, a.amount, " \xB7 requested by ", a.requested, " \xB7 ", a.age)), /*#__PURE__*/React.createElement(Button, {
    size: "sm",
    variant: "quiet",
    onClick: () => setDone(s => ({
      ...s,
      [a.id]: 'declined'
    }))
  }, "Decline"), /*#__PURE__*/React.createElement(Button, {
    size: "sm",
    variant: "accent",
    onClick: () => setDone(s => ({
      ...s,
      [a.id]: 'approved'
    }))
  }, "Approve")))));
}
Object.assign(window, {
  ApprovalsScreen
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/elevionix-app/ApprovalsScreen.jsx", error: String((e && e.message) || e) }); }

// ui_kits/elevionix-app/MattersScreen.jsx
try { (() => {
// Legal vertical — Matters & deadlines. Mono IDs, deadlines in deep orange as explicit dates.
const {
  Badge,
  Eyebrow,
  SealHeading
} = window.ElevionixDesignSystem_f5b95d;
function MattersScreen() {
  const d = window.ELEVIONIX_DATA;
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement(Eyebrow, null, "Legal"), /*#__PURE__*/React.createElement(SealHeading, {
    as: "h2"
  }, "Matters & deadlines"), /*#__PURE__*/React.createElement("p", {
    style: {
      fontFamily: 'var(--font-text)',
      fontSize: 18,
      color: 'var(--brown-mid)',
      margin: '16px 0 0',
      maxWidth: '60ch'
    }
  }, "The legal vertical leans on the mono face; deadlines render in deep orange and are always explicit dates."), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 22,
      display: 'flex',
      flexDirection: 'column',
      gap: 10
    }
  }, d.matters.map(m => /*#__PURE__*/React.createElement("div", {
    key: m.id,
    style: {
      display: 'grid',
      gridTemplateColumns: '160px 1fr auto',
      gap: 16,
      alignItems: 'center',
      background: '#fff',
      border: '1px solid var(--gold-soft)',
      borderRadius: 'var(--r-md)',
      padding: '14px 16px'
    }
  }, /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-data)',
      fontSize: 12,
      color: 'var(--brown-mid)'
    }
  }, m.id), /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("strong", {
    style: {
      color: 'var(--brown)',
      fontFamily: 'var(--font-text)'
    }
  }, m.title), /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'block',
      fontSize: 12,
      color: 'var(--brown-mid)',
      marginTop: 2
    }
  }, m.sub)), m.due ? /*#__PURE__*/React.createElement("span", {
    style: {
      fontFamily: 'var(--font-data)',
      fontSize: 12,
      color: 'var(--orange-deep)'
    }
  }, m.due) : /*#__PURE__*/React.createElement(Badge, {
    variant: m.status
  }, m.statusLabel)))));
}
Object.assign(window, {
  MattersScreen
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/elevionix-app/MattersScreen.jsx", error: String((e && e.message) || e) }); }

// ui_kits/elevionix-app/PlaceholderScreens.jsx
try { (() => {
// Placeholder-style screens + new-workflow modal. Documents/Reports use EmptyState (nothing defined in source).
const {
  EmptyState,
  Field,
  Button,
  Eyebrow,
  SealHeading
} = window.ElevionixDesignSystem_f5b95d;
function DocumentsScreen() {
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement(Eyebrow, null, "Operations"), /*#__PURE__*/React.createElement(SealHeading, {
    as: "h2"
  }, "Documents"), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 20,
      background: 'var(--yellow-card)',
      border: '1px solid var(--gold-soft)',
      borderRadius: 'var(--r-lg)',
      padding: 28
    }
  }, /*#__PURE__*/React.createElement(EmptyState, {
    title: "No documents generated yet",
    description: "Documents produced by your workflows \u2014 invoices, agreements, filings \u2014 collect here.",
    actionLabel: "Connect a template"
  })));
}
function ReportsScreen() {
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement(Eyebrow, null, "Operations"), /*#__PURE__*/React.createElement(SealHeading, {
    as: "h2"
  }, "Reports"), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 20,
      background: 'var(--yellow-card)',
      border: '1px solid var(--gold-soft)',
      borderRadius: 'var(--r-lg)',
      padding: 28
    }
  }, /*#__PURE__*/React.createElement(EmptyState, {
    title: "Reporting is being prepared",
    description: "Once workflows have a month of runs, savings and throughput reports appear here."
  })));
}
function NewWorkflowModal({
  onClose
}) {
  return /*#__PURE__*/React.createElement("div", {
    onClick: onClose,
    style: {
      position: 'fixed',
      inset: 0,
      background: 'rgba(51,32,13,.42)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 20
    }
  }, /*#__PURE__*/React.createElement("div", {
    onClick: e => e.stopPropagation(),
    style: {
      width: 460,
      background: 'var(--yellow-card)',
      border: '1px solid var(--gold-soft)',
      borderRadius: 'var(--r-lg)',
      padding: 26,
      boxShadow: 'var(--shadow)'
    }
  }, /*#__PURE__*/React.createElement(Eyebrow, null, "New automation"), /*#__PURE__*/React.createElement(SealHeading, {
    as: "h3"
  }, "Map a process"), /*#__PURE__*/React.createElement("div", {
    style: {
      marginTop: 18,
      display: 'flex',
      flexDirection: 'column',
      gap: 16
    }
  }, /*#__PURE__*/React.createElement(Field, {
    label: "Workflow name",
    placeholder: "e.g. Invoice \u2192 approval \u2192 Tally"
  }), /*#__PURE__*/React.createElement(Field, {
    label: "Owner",
    defaultValue: "Priya"
  })), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      gap: 10,
      justifyContent: 'flex-end',
      marginTop: 22
    }
  }, /*#__PURE__*/React.createElement(Button, {
    variant: "quiet",
    onClick: onClose
  }, "Cancel"), /*#__PURE__*/React.createElement(Button, {
    variant: "accent",
    onClick: onClose
  }, "Create workflow"))));
}
Object.assign(window, {
  DocumentsScreen,
  ReportsScreen,
  NewWorkflowModal
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/elevionix-app/PlaceholderScreens.jsx", error: String((e && e.message) || e) }); }

// ui_kits/elevionix-app/WorkflowsScreen.jsx
try { (() => {
function _extends() { return _extends = Object.assign ? Object.assign.bind() : function (n) { for (var e = 1; e < arguments.length; e++) { var t = arguments[e]; for (var r in t) ({}).hasOwnProperty.call(t, r) && (n[r] = t[r]); } return n; }, _extends.apply(null, arguments); }
// Workflows dashboard — stat tiles + workflow table. Composes StatCard, Badge, Button, Eyebrow, SealHeading.
const {
  StatCard,
  Badge,
  Button,
  Eyebrow,
  SealHeading
} = window.ElevionixDesignSystem_f5b95d;
function WorkflowsScreen({
  onNewWorkflow
}) {
  const d = window.ELEVIONIX_DATA;
  const th = {
    fontFamily: 'var(--font-data)',
    fontSize: 10,
    letterSpacing: '.12em',
    textTransform: 'uppercase',
    color: 'var(--gold)',
    textAlign: 'left',
    padding: '10px 14px',
    borderBottom: '1px solid var(--gold-soft)',
    fontWeight: 500
  };
  const td = {
    padding: '12px 14px',
    borderBottom: '1px solid var(--hairline)',
    fontSize: 14,
    color: 'var(--brown)'
  };
  const labels = {
    active: 'Active',
    pending: 'Awaiting review',
    draft: 'Draft'
  };
  return /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'flex',
      alignItems: 'flex-end',
      justifyContent: 'space-between',
      marginBottom: 20
    }
  }, /*#__PURE__*/React.createElement("div", null, /*#__PURE__*/React.createElement(Eyebrow, null, "Operations"), /*#__PURE__*/React.createElement(SealHeading, {
    as: "h2"
  }, "Workflows \u2014 this month")), /*#__PURE__*/React.createElement(Button, {
    variant: "accent",
    onClick: onNewWorkflow
  }, "Start automation")), /*#__PURE__*/React.createElement("div", {
    style: {
      display: 'grid',
      gridTemplateColumns: 'repeat(4,1fr)',
      gap: 14,
      marginBottom: 22
    }
  }, d.stats.map(s => /*#__PURE__*/React.createElement(StatCard, _extends({
    key: s.label
  }, s)))), /*#__PURE__*/React.createElement("table", {
    style: {
      width: '100%',
      borderCollapse: 'collapse',
      background: '#fff',
      border: '1px solid var(--gold-soft)',
      borderRadius: 'var(--r-md)',
      overflow: 'hidden'
    }
  }, /*#__PURE__*/React.createElement("thead", null, /*#__PURE__*/React.createElement("tr", null, /*#__PURE__*/React.createElement("th", {
    style: th
  }, "Workflow"), /*#__PURE__*/React.createElement("th", {
    style: th
  }, "Owner"), /*#__PURE__*/React.createElement("th", {
    style: th
  }, "Status"), /*#__PURE__*/React.createElement("th", {
    style: {
      ...th,
      textAlign: 'right'
    }
  }, "Runs / mo"))), /*#__PURE__*/React.createElement("tbody", null, d.workflows.map((w, i) => /*#__PURE__*/React.createElement("tr", {
    key: w.name
  }, /*#__PURE__*/React.createElement("td", {
    style: i === d.workflows.length - 1 ? {
      ...td,
      borderBottom: 0
    } : td
  }, w.name, /*#__PURE__*/React.createElement("span", {
    style: {
      display: 'block',
      fontSize: 12,
      color: 'var(--brown-mid)'
    }
  }, w.team)), /*#__PURE__*/React.createElement("td", {
    style: i === d.workflows.length - 1 ? {
      ...td,
      borderBottom: 0
    } : td
  }, w.owner), /*#__PURE__*/React.createElement("td", {
    style: i === d.workflows.length - 1 ? {
      ...td,
      borderBottom: 0
    } : td
  }, /*#__PURE__*/React.createElement(Badge, {
    variant: w.status
  }, labels[w.status])), /*#__PURE__*/React.createElement("td", {
    style: {
      ...(i === d.workflows.length - 1 ? {
        ...td,
        borderBottom: 0
      } : td),
      fontFamily: 'var(--font-data)',
      fontSize: 13,
      textAlign: 'right'
    }
  }, w.runs))))));
}
Object.assign(window, {
  WorkflowsScreen
});
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/elevionix-app/WorkflowsScreen.jsx", error: String((e && e.message) || e) }); }

// ui_kits/elevionix-app/data.js
try { (() => {
// Elevionix app — sample data (fake). Indian SMB / legal automation context.
window.ELEVIONIX_DATA = {
  stats: [{
    label: 'Active workflows',
    value: '9',
    delta: 'All running'
  }, {
    label: 'Tasks automated',
    value: '1,284',
    delta: '+212 this month'
  }, {
    label: 'Hours saved',
    value: '96',
    delta: 'This month'
  }, {
    label: 'Pending approvals',
    value: '4',
    delta: '2 overdue',
    warn: true
  }],
  workflows: [{
    name: 'Invoice → approval → Tally',
    team: 'Accounts',
    owner: 'Priya',
    status: 'active',
    runs: '340'
  }, {
    name: 'New-client onboarding',
    team: 'Sales',
    owner: 'Rohit',
    status: 'active',
    runs: '28'
  }, {
    name: 'GST filing checklist',
    team: 'Compliance',
    owner: 'Priya',
    status: 'pending',
    runs: '1'
  }, {
    name: 'Vendor agreement renewals',
    team: 'Legal',
    owner: 'Aman',
    status: 'draft',
    runs: '—'
  }, {
    name: 'Payroll run → payslips',
    team: 'HR',
    owner: 'Sana',
    status: 'active',
    runs: '12'
  }],
  approvals: [{
    id: 'APR-5521',
    title: 'Invoice #INV-2048 — Kartar Traders',
    amount: '₹1,20,000',
    requested: 'Priya',
    age: '2 days overdue',
    warn: true
  }, {
    id: 'APR-5523',
    title: 'Vendor renewal — CloudNet hosting',
    amount: '₹48,000',
    requested: 'Aman',
    age: '1 day overdue',
    warn: true
  }, {
    id: 'APR-5527',
    title: 'New-client onboarding — Mehta & Co',
    amount: '—',
    requested: 'Rohit',
    age: 'Today'
  }, {
    id: 'APR-5529',
    title: 'Expense claim — travel, Q2',
    amount: '₹9,400',
    requested: 'Sana',
    age: 'Today'
  }],
  matters: [{
    id: 'MTR-2026-0148',
    title: 'Sharma vs. Regional Transport — appeal',
    sub: 'Drafting stage · assigned to Adv. Mehta',
    due: 'Due 24 Jul 2026'
  }, {
    id: 'MTR-2026-0151',
    title: 'Lease renewal — Kartar Traders',
    sub: 'Client review · documents sent 16 Jul',
    due: 'Due 31 Jul 2026'
  }, {
    id: 'MTR-2026-0139',
    title: 'Trademark objection response',
    sub: 'Filed · awaiting registry',
    status: 'active',
    statusLabel: 'On track'
  }, {
    id: 'MTR-2026-0155',
    title: 'Employment contract — new hires',
    sub: 'Awaiting partner sign-off',
    status: 'pending',
    statusLabel: 'Awaiting review'
  }]
};
})(); } catch (e) { __ds_ns.__errors.push({ path: "ui_kits/elevionix-app/data.js", error: String((e && e.message) || e) }); }

__ds_ns.Wordmark = __ds_scope.Wordmark;

__ds_ns.Button = __ds_scope.Button;

__ds_ns.Badge = __ds_scope.Badge;

__ds_ns.EmptyState = __ds_scope.EmptyState;

__ds_ns.Field = __ds_scope.Field;

__ds_ns.Panel = __ds_scope.Panel;

__ds_ns.StatCard = __ds_scope.StatCard;

__ds_ns.Eyebrow = __ds_scope.Eyebrow;

__ds_ns.SealHeading = __ds_scope.SealHeading;

})();
