"use client";

import React, { useId, useState } from "react";

import styles from "./entity-resolution-panel.module.css";

export type EntityResolutionStatus = "RESOLVED" | "AMBIGUOUS" | "UNCONFIRMED";

export type EntityMatchReason = {
  code: string;
  detail: string;
};

export type EntityCandidate = {
  company_id: string;
  canonical_name: string;
  country_code: string;
  entity_type: string;
  confidence: number;
  match_reasons: EntityMatchReason[];
  evidence_refs: string[];
};

export type EntityLegalRecord = {
  legal_name: string;
  registration_number: string;
  jurisdiction: string;
  legal_status: string;
  source: string;
  retrieved_at: string;
  freshness: string;
};

export type EntityResolution = {
  status: EntityResolutionStatus;
  selected_company_id: string | null;
  research_allowed: boolean;
  abstention_reason: string | null;
  match_reasons: EntityMatchReason[];
  candidates: EntityCandidate[];
  legal_record?: EntityLegalRecord;
};

export type EntityResolutionPanelProps = {
  resolution: EntityResolution;
  onSelect?: (companyId: string, candidate: EntityCandidate) => void;
  onRetry?: () => void;
  className?: string;
};

const COUNTRY_NAMES: Record<string, string> = {
  GB: "United Kingdom",
  IN: "India",
  US: "United States",
};

const STATUS_COPY: Record<EntityResolutionStatus, { icon: string; label: string; description: string }> = {
  RESOLVED: {
    icon: "✓",
    label: "Resolved",
    description: "A canonical legal entity has been identified.",
  },
  AMBIGUOUS: {
    icon: "?",
    label: "Ambiguous",
    description: "More than one legal entity matches the supplied identifiers.",
  },
  UNCONFIRMED: {
    icon: "i",
    label: "Unconfirmed",
    description: "There is not enough identity evidence to confirm a legal entity.",
  },
};

function formatLabel(value: string): string {
  return value
    .toLowerCase()
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

function formatCountry(code: string): string {
  const normalizedCode = code.toUpperCase();
  return COUNTRY_NAMES[normalizedCode] ? `${COUNTRY_NAMES[normalizedCode]} (${normalizedCode})` : normalizedCode;
}

function formatConfidence(confidence: number): string {
  if (!Number.isFinite(confidence)) return "Confidence unavailable";
  return `${Math.round(Math.max(0, Math.min(1, confidence)) * 100)}%`;
}

function formatRetrievedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en", { dateStyle: "medium", timeZone: "UTC" }).format(date);
}

function EvidenceRefs({ refs }: { refs: string[] }) {
  if (refs.length === 0) return <span className={styles.mutedValue}>No evidence reference recorded</span>;

  return (
    <ul className={styles.evidenceList} aria-label="Evidence references">
      {refs.map((ref) => (
        <li key={ref}>
          <code>{ref}</code>
        </li>
      ))}
    </ul>
  );
}

function MatchReasons({ reasons }: { reasons: EntityMatchReason[] }) {
  if (reasons.length === 0) return <span className={styles.mutedValue}>No match reason recorded</span>;

  return (
    <ul className={styles.reasonList}>
      {reasons.map((reason, index) => (
        <li key={`${reason.code}-${index}`}>
          <strong>{formatLabel(reason.code)}</strong>
          <span>{reason.detail}</span>
        </li>
      ))}
    </ul>
  );
}

function CandidateDetails({ candidate }: { candidate: EntityCandidate }) {
  return (
    <dl className={styles.candidateDetails}>
      <div>
        <dt>Country</dt>
        <dd>{formatCountry(candidate.country_code)}</dd>
      </div>
      <div>
        <dt>Entity type</dt>
        <dd>{formatLabel(candidate.entity_type)}</dd>
      </div>
      <div>
        <dt>Confidence</dt>
        <dd className={styles.confidenceValue}>{formatConfidence(candidate.confidence)}</dd>
      </div>
      <div className={styles.detailWide}>
        <dt>Why it matched</dt>
        <dd><MatchReasons reasons={candidate.match_reasons} /></dd>
      </div>
      <div className={styles.detailWide}>
        <dt>Evidence references</dt>
        <dd><EvidenceRefs refs={candidate.evidence_refs} /></dd>
      </div>
    </dl>
  );
}

function ResolutionHeader({ resolution }: { resolution: EntityResolution }) {
  const copy = STATUS_COPY[resolution.status];

  return (
    <header className={styles.panelHeader}>
      <div>
        <p className={styles.eyebrow}>Entity resolution</p>
        <h2 id="entity-resolution-title">Confirm the legal entity</h2>
        <p className={styles.headerDescription}>{copy.description}</p>
      </div>
      <div className={`${styles.statusBadge} ${styles[`status${resolution.status}`]}`} role="status" aria-live="polite">
        <span className={styles.statusIcon} aria-hidden="true">{copy.icon}</span>
        <span>{copy.label}</span>
        <span className={styles.statusCode}>{resolution.status}</span>
      </div>
    </header>
  );
}

function ResolutionReasons({ reasons }: { reasons: EntityMatchReason[] }) {
  if (reasons.length === 0) return null;

  return (
    <section className={styles.resolutionReasons} aria-labelledby="resolution-reasons-title">
      <h3 id="resolution-reasons-title">Resolution notes</h3>
      <MatchReasons reasons={reasons} />
    </section>
  );
}

function ResearchGate({ allowed }: { allowed: boolean }) {
  return (
    <aside className={`${styles.researchGate} ${allowed ? styles.researchGateOpen : styles.researchGateBlocked}`} aria-label="Research access">
      <span className={styles.gateIcon} aria-hidden="true">{allowed ? "✓" : "!"}</span>
      <div>
        <strong>{allowed ? "Research may proceed" : "Research is blocked"}</strong>
        <p>{allowed ? "The parent workspace can now start a research run for this company ID." : "Choose and confirm one legal entity before research begins."}</p>
      </div>
    </aside>
  );
}

function LegalRecord({ record }: { record: EntityLegalRecord }) {
  return (
    <section className={styles.legalRecord} aria-labelledby="legal-record-title">
      <div className={styles.subsectionHeading}>
        <div>
          <p className={styles.eyebrow}>Registry evidence</p>
          <h3 id="legal-record-title">Legal record</h3>
        </div>
        <span className={styles.freshnessLabel}>{formatLabel(record.freshness)}</span>
      </div>
      <dl className={styles.legalDetails}>
        <div><dt>Legal name</dt><dd>{record.legal_name}</dd></div>
        <div><dt>Registration number</dt><dd><code>{record.registration_number}</code></dd></div>
        <div><dt>Jurisdiction</dt><dd>{formatCountry(record.jurisdiction)}</dd></div>
        <div><dt>Legal status</dt><dd>{formatLabel(record.legal_status)}</dd></div>
        <div><dt>Source</dt><dd>{formatLabel(record.source)}</dd></div>
        <div><dt>Retrieved</dt><dd>{formatRetrievedAt(record.retrieved_at)}</dd></div>
      </dl>
    </section>
  );
}

function UnconfirmedState({ resolution, onRetry }: { resolution: EntityResolution; onRetry?: () => void }) {
  return (
    <div className={styles.stateBody}>
      <div className={styles.stateLead}>
        <span className={styles.stateIcon} aria-hidden="true">i</span>
        <div>
          <h3>Insufficient evidence</h3>
          <p>{resolution.abstention_reason ?? "The legal entity could not be confirmed from the supplied identifiers."}</p>
        </div>
      </div>
      <div className={styles.nextStep}>
        <strong>What to try next</strong>
        <p>Add a country or jurisdiction, ticker, official domain, or registry identifier, then run entity resolution again.</p>
        {onRetry ? <button type="button" className={styles.secondaryButton} onClick={onRetry}>Try again with more identifiers</button> : null}
      </div>
      <ResolutionReasons reasons={resolution.match_reasons} />
      <ResearchGate allowed={false} />
    </div>
  );
}

function AmbiguousState({ resolution, onSelect }: { resolution: EntityResolution; onSelect?: EntityResolutionPanelProps["onSelect"] }) {
  const groupId = useId();
  const [selectedId, setSelectedId] = useState<string | null>(resolution.selected_company_id);
  const selectedCandidate = resolution.candidates.find((candidate) => candidate.company_id === selectedId);

  function confirmSelection() {
    if (selectedCandidate) onSelect?.(selectedCandidate.company_id, selectedCandidate);
  }

  return (
    <div className={styles.stateBody}>
      <div className={styles.stateLead}>
        <span className={styles.stateIcon} aria-hidden="true">?</span>
        <div>
          <h3>Choose the legal entity</h3>
          <p>{resolution.abstention_reason ?? "Select the company that matches the research subject."}</p>
        </div>
      </div>

      <fieldset className={styles.candidateGroup}>
        <legend>Candidate companies</legend>
        <p className={styles.fieldHint}>Review the jurisdiction and evidence before allowing research to begin.</p>
        <div className={styles.candidateList}>
          {resolution.candidates.map((candidate) => {
            const inputId = `${groupId}-${candidate.company_id}`;
            const isSelected = selectedId === candidate.company_id;
            return (
              <div className={`${styles.candidateCard} ${isSelected ? styles.candidateCardSelected : ""}`} key={candidate.company_id}>
                <label className={styles.candidateLabel} htmlFor={inputId}>
                  <input
                    id={inputId}
                    name={groupId}
                    type="radio"
                    value={candidate.company_id}
                    checked={isSelected}
                    onChange={() => setSelectedId(candidate.company_id)}
                    aria-label={`Select ${candidate.canonical_name}`}
                  />
                  <span className={styles.radioMark} aria-hidden="true" />
                  <span className={styles.candidateName}>{candidate.canonical_name}</span>
                </label>
                <CandidateDetails candidate={candidate} />
              </div>
            );
          })}
        </div>
      </fieldset>

      <ResolutionReasons reasons={resolution.match_reasons} />
      <ResearchGate allowed={false} />
      <div className={styles.confirmRow}>
        <p>Selection is explicit. The parent can persist this company ID at the authenticated API boundary.</p>
        <button type="button" className={styles.primaryButton} onClick={confirmSelection} disabled={!selectedCandidate}>
          Confirm selected entity
        </button>
      </div>
    </div>
  );
}

function ResolvedState({ resolution }: { resolution: EntityResolution }) {
  const candidate = resolution.candidates.find((item) => item.company_id === resolution.selected_company_id) ?? resolution.candidates[0];

  return (
    <div className={styles.stateBody}>
      <div className={styles.stateLead}>
        <span className={styles.stateIcon} aria-hidden="true">✓</span>
        <div>
          <h3>{candidate?.canonical_name ?? "Canonical entity identified"}</h3>
          <p>{resolution.abstention_reason ?? "The supplied identifiers matched one canonical legal entity."}</p>
        </div>
      </div>
      {candidate ? <CandidateDetails candidate={candidate} /> : null}
      <ResolutionReasons reasons={resolution.match_reasons} />
      {resolution.legal_record ? <LegalRecord record={resolution.legal_record} /> : null}
      <ResearchGate allowed={resolution.research_allowed} />
    </div>
  );
}

export function EntityResolutionPanel({ resolution, onSelect, onRetry, className }: EntityResolutionPanelProps) {
  const panelClassName = [styles.panel, className].filter(Boolean).join(" ");

  return (
    <section className={panelClassName} aria-labelledby="entity-resolution-title">
      <ResolutionHeader resolution={resolution} />
      {resolution.status === "AMBIGUOUS" ? <AmbiguousState resolution={resolution} onSelect={onSelect} /> : null}
      {resolution.status === "UNCONFIRMED" ? <UnconfirmedState resolution={resolution} onRetry={onRetry} /> : null}
      {resolution.status === "RESOLVED" ? <ResolvedState resolution={resolution} /> : null}
    </section>
  );
}

export default EntityResolutionPanel;
