"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Demonstration roles only. This selector exists so a reviewer can see the
// application boundary reject an action. It is not authentication.
const DEMO_ROLES = [
  { value: "viewer", label: "Ажиглагч (эрхгүй)" },
  { value: "reviewer", label: "Хянагч" },
  { value: "approver", label: "Батлах эрх бүхий хүн" },
];

export default function DecisionPanel({ tenderId }) {
  const router = useRouter();
  const [role, setRole] = useState("reviewer");
  const [draft, setDraft] = useState(null);
  const [approved, setApproved] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function request(path, options) {
    const response = await fetch(`${apiUrl}${path}`, options);
    let payload = {};
    try {
      payload = await response.json();
    } catch {
      payload = {};
    }
    if (!response.ok) {
      throw new Error(payload.detail || `Хүсэлт амжилтгүй боллоо (${response.status}).`);
    }
    return payload;
  }

  async function createDraft() {
    setBusy(true);
    setError("");
    setApproved(false);
    try {
      const payload = await request(`/api/v1/tenders/${tenderId}/draft-summary`, {
        method: "POST",
        headers: { "X-Role": role },
      });
      setDraft(payload);
      router.refresh();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  async function approveDraft() {
    if (!draft) return;
    setBusy(true);
    setError("");
    try {
      await request(`/api/v1/tenders/${tenderId}/approve`, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Role": role },
        body: JSON.stringify({
          decision_id: draft.decision_id,
          approved_by: "Жишээ эрх бүхий хянагч",
          note: "Жишээ орчинд хүний хяналтаар баталлаа.",
        }),
      });
      setApproved(true);
      router.refresh();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="section-title">
        <h2>3. AI төсөл ба хүний шийдвэр</h2>
        <p>
          AI зөвхөн дээрх баримт, дүрмийн шалгалтад тулгуурлан төсөл бичнэ. Төсөл нь албан ёсны
          шийдвэр биш. Батлах үйлдэл тусдаа бөгөөд зөвхөн эрх бүхий хүн хийнэ.
        </p>
      </div>

      <div className="card">
        <div className="panel-head">
          <h3>Дүгнэлтийн төсөл</h3>
          <span className="badge quiet">Үзүүлэнгийн горим</span>
        </div>

        <div className="role-row">
          <label htmlFor="demo-role">Үзүүлэнгийн эрх:</label>
          <select
            id="demo-role"
            value={role}
            onChange={(event) => setRole(event.target.value)}
            disabled={busy}
          >
            {DEMO_ROLES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div className="buttons">
          <button className="button" onClick={createDraft} disabled={busy}>
            {busy ? "Түр хүлээнэ үү…" : "AI-аар төсөл бэлтгэх"}
          </button>
          {draft && !approved ? (
            <button className="button secondary" onClick={approveDraft} disabled={busy}>
              {busy ? "Түр хүлээнэ үү…" : "Хүний шийдвэрээр батлах"}
            </button>
          ) : null}
        </div>

        {error ? (
          <div className="notice error" role="alert" style={{ marginTop: "14px" }}>
            {error}
          </div>
        ) : null}

        {draft ? (
          <div className="draft">
            <div className="draft-meta">
              <span>Төлөв: {approved ? "Батлагдсан" : "Төсөл"}</span>
              <span>Provider: {draft.provider}</span>
              <span>Model: {draft.model}</span>
              <span>Шийдвэр №{draft.decision_id}</span>
            </div>
            <p className="draft-text">{draft.summary_mn}</p>
            {approved ? (
              <div className="notice accent">
                Хүний баталгаажуулалт аудитын бүртгэлд хадгалагдлаа.
              </div>
            ) : (
              <div className="notice attention">{draft.note_mn}</div>
            )}
          </div>
        ) : null}
      </div>
    </>
  );
}
