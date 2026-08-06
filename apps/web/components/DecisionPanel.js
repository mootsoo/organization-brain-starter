"use client";

import { useState } from "react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function DecisionPanel({ tenderId }) {
  const [draft, setDraft] = useState(null);
  const [approved, setApproved] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function createDraft() {
    setLoading(true);
    setError("");
    setApproved(false);

    try {
      const response = await fetch(`${apiUrl}/api/v1/tenders/${tenderId}/draft-summary`, {
        method: "POST",
        headers: { "X-Role": "reviewer" },
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || "Төсөл бэлтгэж чадсангүй.");
      }
      setDraft(payload);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  async function approveDraft() {
    if (!draft) return;
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${apiUrl}/api/v1/tenders/${tenderId}/approve`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Role": "approver",
        },
        body: JSON.stringify({
          decision_id: draft.decision_id,
          approved_by: "Демо эрх бүхий хянагч",
          note: "Жишээ орчинд хүний хяналтаар батлав.",
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload.detail || "Баталгаажуулж чадсангүй.");
      }
      setApproved(true);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="decision-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">AI туслах + хүний шийдвэр</span>
          <h2>Дүгнэлтийн төсөл</h2>
        </div>
        <span className="demo-label">Demo mode</span>
      </div>

      <p className="panel-explanation">
        AI зөвхөн харагдаж буй бүтэцтэй мэдээллээс төсөл бэлтгэнэ. Үүний дараа тусдаа хүний
        баталгаажуулалт шаардлагатай.
      </p>

      {!draft ? (
        <button className="button primary" onClick={createDraft} disabled={loading}>
          {loading ? "Бэлтгэж байна…" : "AI-аар төсөл бэлтгэх"}
        </button>
      ) : (
        <div className="draft-box">
          <div className="draft-meta">
            <span>Provider: {draft.provider}</span>
            <span>Status: {approved ? "approved" : draft.status}</span>
          </div>
          <p>{draft.summary_mn}</p>
          {!approved ? (
            <button className="button approval" onClick={approveDraft} disabled={loading}>
              {loading ? "Хадгалж байна…" : "Хүний шийдвэрээр батлах"}
            </button>
          ) : (
            <div className="approval-message">Хүний баталгаажуулалт аудитын бүртгэлд хадгалагдлаа.</div>
          )}
        </div>
      )}

      {error ? <div className="notice error compact">{error}</div> : null}
    </section>
  );
}
