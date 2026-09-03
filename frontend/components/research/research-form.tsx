"use client";

import { FormEvent, useId, useState } from "react";

import {
  DEPTH_OPTIONS,
  FOCUS_OPTIONS,
  RESEARCH_MODE_OPTIONS,
  type CreateReportRequest,
  type ResearchDepth,
  type ResearchMode,
} from "./research-types";
import styles from "./research-workspace.module.css";

type ResearchFormProps = {
  disabled?: boolean;
  error?: string | null;
  initialQuery?: string;
  initialMode?: ResearchMode;
  onSubmit: (request: CreateReportRequest) => Promise<void>;
};

type FormValues = {
  title: string;
  query: string;
  countryCode: string;
  ticker: string;
  domain: string;
  focus: string[];
  depth: ResearchDepth;
  researchMode: ResearchMode;
};

const initialValues: FormValues = {
  title: "",
  query: "",
  countryCode: "",
  ticker: "",
  domain: "",
  focus: ["financials"],
  depth: "STANDARD",
  researchMode: "INITIATION",
};

function inputError(values: FormValues): string | null {
  if (!values.query.trim()) return "Enter a company name, ticker, or domain to begin.";
  if (values.countryCode && !/^[a-z]{2}$/i.test(values.countryCode.trim())) {
    return "Country code must be two letters, such as US, IN, or GB.";
  }
  if (values.domain && !/^(https?:\/\/)?([a-z0-9-]+\.)+[a-z]{2,}(\/.*)?$/i.test(values.domain.trim())) {
    return "Enter a domain such as example.com.";
  }
  if (values.focus.length === 0) return "Choose at least one research focus.";
  return null;
}

function generatedTitle(values: FormValues): string {
  const focus = values.focus.includes("full_research")
    ? "Full Research"
    : FOCUS_OPTIONS.find((option) => option.value === values.focus[0])?.label ?? "Research";
  return `${values.query.trim()} - ${focus}`;
}

export function ResearchForm({ disabled = false, error, initialQuery = "", initialMode = "INITIATION", onSubmit }: ResearchFormProps) {
  const [values, setValues] = useState<FormValues>(() => ({ ...initialValues, query: initialQuery.trim(), researchMode: initialMode }));
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const queryId = useId();
  const titleId = useId();
  const countryId = useId();
  const tickerId = useId();
  const domainId = useId();
  const formErrorId = useId();

  function update<K extends keyof FormValues>(key: K, value: FormValues[K]) {
    setValues((current) => ({ ...current, [key]: value }));
    setValidationError(null);
  }

  function toggleFocus(value: string) {
    setValues((current) => {
      if (value === "full_research") return { ...current, focus: ["full_research"] };
      const withoutFull = current.focus.filter((item) => item !== "full_research");
      const focus = withoutFull.includes(value)
        ? withoutFull.filter((item) => item !== value)
        : [...withoutFull, value];
      return { ...current, focus };
    });
    setValidationError(null);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const message = inputError(values);
    if (message) {
      setValidationError(message);
      return;
    }

    setIsSubmitting(true);
    setValidationError(null);
    try {
      await onSubmit({
        title: values.title.trim() || generatedTitle(values),
        subject: {
          query: values.query.trim(),
          ...(values.countryCode.trim() ? { country_code: values.countryCode.trim().toUpperCase() } : {}),
          ...(values.ticker.trim() ? { ticker: values.ticker.trim().toUpperCase() } : {}),
          ...(values.domain.trim() ? { domain: values.domain.trim() } : {}),
        },
        focus: values.focus,
        depth: values.depth,
        research_mode: values.researchMode,
      });
      setValues(initialValues);
    } catch {
      // The parent owns the human-readable API error state; keep form values for correction/retry.
    } finally {
      setIsSubmitting(false);
    }
  }

  const formError = validationError ?? error;
  const formErrorDescription = formError ? formErrorId : undefined;

  return (
    <form className={styles.researchForm} onSubmit={handleSubmit} noValidate>
      <div className={styles.formHeader}>
        <div>
          <p className={styles.eyebrow}>Create workspace</p>
          <h2 id="create-research-title">Start with a company, not a conclusion.</h2>
          <p>Capture the subject and research intent first. Evidence comes after the workspace is created.</p>
        </div>
        <span className={styles.formStep} aria-label="Step 1 of 2">01 / 02</span>
      </div>

      {formError ? (
        <div className={styles.alert} id={formErrorId} role="alert">
          <span className={styles.alertIcon} aria-hidden="true">!</span>
          <span>{formError}</span>
        </div>
      ) : null}

      <div className={styles.formGrid}>
        <div className={styles.field}>
          <label htmlFor={queryId}>Company name, ticker, or domain <span aria-hidden="true">*</span></label>
          <input
            id={queryId}
            name="query"
            value={values.query}
            onChange={(event) => update("query", event.target.value)}
            placeholder="e.g. NVIDIA"
            autoComplete="organization"
            aria-describedby={formErrorDescription}
            disabled={disabled || isSubmitting}
            required
          />
          <span className={styles.fieldHint}>A name is enough. Add identifiers below when you have them.</span>
        </div>
        <div className={styles.field}>
          <label htmlFor={titleId}>Workspace title <span className={styles.optional}>(optional)</span></label>
          <input
            id={titleId}
            name="title"
            value={values.title}
            onChange={(event) => update("title", event.target.value)}
            placeholder="Generated from your subject"
            disabled={disabled || isSubmitting}
          />
          <span className={styles.fieldHint}>Use a name that will make this research easy to revisit.</span>
        </div>
        <div className={styles.field}>
          <label htmlFor={countryId}>Country / jurisdiction <span className={styles.optional}>(optional)</span></label>
          <input
            id={countryId}
            name="country_code"
            value={values.countryCode}
            onChange={(event) => update("countryCode", event.target.value)}
            placeholder="US"
            maxLength={2}
            autoCapitalize="characters"
            aria-describedby={formErrorDescription}
            disabled={disabled || isSubmitting}
          />
        </div>
        <div className={styles.field}>
          <label htmlFor={tickerId}>Ticker <span className={styles.optional}>(optional)</span></label>
          <input
            id={tickerId}
            name="ticker"
            value={values.ticker}
            onChange={(event) => update("ticker", event.target.value)}
            placeholder="AAPL"
            autoCapitalize="characters"
            disabled={disabled || isSubmitting}
          />
        </div>
        <div className={`${styles.field} ${styles.fieldWide}`}>
          <label htmlFor={domainId}>Official domain <span className={styles.optional}>(optional)</span></label>
          <input
            id={domainId}
            name="domain"
            value={values.domain}
            onChange={(event) => update("domain", event.target.value)}
            placeholder="company.com"
            inputMode="url"
            aria-describedby={formErrorDescription}
            disabled={disabled || isSubmitting}
          />
          <span className={styles.fieldHint}>This is a candidate identifier until the system confirms it.</span>
        </div>
      </div>

      <fieldset className={styles.choiceGroup}>
        <legend>Research mode</legend>
        <p className={styles.choiceIntro}>Choose the work product before selecting its depth.</p>
        <div className={styles.depthGrid}>
          {RESEARCH_MODE_OPTIONS.map((option) => (
            <label className={`${styles.depthCard} ${values.researchMode === option.value ? styles.depthCardSelected : ""}`} key={option.value}>
              <input type="radio" name="research-mode" value={option.value} checked={values.researchMode === option.value} onChange={() => update("researchMode", option.value)} disabled={disabled || isSubmitting} />
              <span><strong>{option.label}</strong><small>{option.description}</small></span><span className={styles.radioMark} aria-hidden="true" />
            </label>
          ))}
        </div>
      </fieldset>

      <fieldset className={styles.choiceGroup}>
        <legend>Research focus</legend>
        <p className={styles.choiceIntro}>Choose what should be prioritized in the first run.</p>
        <div className={styles.focusGrid}>
          {FOCUS_OPTIONS.map((option) => {
            const checked = values.focus.includes(option.value);
            return (
              <label className={`${styles.choiceCard} ${checked ? styles.choiceCardSelected : ""}`} key={option.value}>
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggleFocus(option.value)}
                  disabled={disabled || isSubmitting}
                />
                <span className={styles.choiceCheck} aria-hidden="true">{checked ? "✓" : ""}</span>
                <span>
                  <strong>{option.label}</strong>
                  <small>{option.description}</small>
                </span>
              </label>
            );
          })}
        </div>
      </fieldset>

      <fieldset className={styles.choiceGroup}>
        <legend>Research depth</legend>
        <p className={styles.choiceIntro}>Depth controls how much work is queued after creation.</p>
        <div className={styles.depthGrid}>
          {DEPTH_OPTIONS.map((option) => (
            <label className={`${styles.depthCard} ${values.depth === option.value ? styles.depthCardSelected : ""}`} key={option.value}>
              <input
                type="radio"
                name="depth"
                value={option.value}
                checked={values.depth === option.value}
                onChange={() => update("depth", option.value)}
                disabled={disabled || isSubmitting}
              />
              <span>
                <strong>{option.label}</strong>
                <small>{option.description}</small>
              </span>
              <span className={styles.radioMark} aria-hidden="true" />
            </label>
          ))}
        </div>
      </fieldset>

      <div className={styles.formFooter}>
        <p><span aria-hidden="true">↳</span> The new workspace starts as <strong>DRAFT</strong>.</p>
        <button className={styles.primaryButton} type="submit" disabled={disabled || isSubmitting}>
          <span aria-hidden="true">+</span>
          {isSubmitting ? "Creating workspace…" : "Create research workspace"}
        </button>
      </div>
    </form>
  );
}
