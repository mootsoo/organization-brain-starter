import { notFound } from "next/navigation";

import DecisionPanel from "../../../components/DecisionPanel";
import SiteHeader from "../../../components/SiteHeader";
import { getTender } from "../../../lib/api";

export const dynamic = "force-dynamic";

const stageLabels = {
  registration: "Бүртгэл",
  rule_check: "Дүрмийн шалгалт",
  human_review: "Хүний хяналт",
  approved: "Батлагдсан",
};

const decisionStatusLabels = {
  draft: "Төсөл",
  approved: "Батлагдсан",
  rejected: "Татгалзсан",
};

function formatMnt(value) {
  return `${new Intl.NumberFormat("mn-MN").format(Number(value))} ₮`;
}

function formatDateTime(value) {
  if (!value) return "—";
  return new Date(value).toLocaleString("mn-MN", { timeZone: "Asia/Ulaanbaatar" });
}

function formatDate(value) {
  if (!value) return "—";
  return new Date(value).toLocaleDateString("mn-MN", { timeZone: "Asia/Ulaanbaatar" });
}

export default async function TenderPage({ params }) {
  const { id } = await params;
  let data;

  try {
    data = await getTender(id);
  } catch {
    notFound();
  }

  const { tender, submissions, checks, findings, decisions, audit_events: auditEvents } = data;
  const attention = findings.filter((item) => item.severity === "attention");

  return (
    <>
      <SiteHeader note="← Нүүр хуудас" />

      <main className="container page">
        <div className="lede">
          <p className="empty">{tender.code}</p>
          <h1>{tender.title_mn}</h1>
          <p>{tender.purpose_mn}</p>
          <p style={{ marginTop: "12px" }}>
            <span className={`badge ${tender.stage === "approved" ? "" : "quiet"}`}>
              {stageLabels[tender.stage] || tender.stage}
            </span>
          </p>
        </div>

        {/* 1. Facts held in the database ------------------------------------ */}
        <section className="section">
          <div className="section-title">
            <h2>1. Бүртгэлтэй баримт</h2>
            <p>Эдгээр нь мэдээллийн санд хадгалагдсан тоо баримт. AI эдгээрийг өөрчилдөггүй.</p>
          </div>

          <div className="facts">
            <article className="fact">
              <small>Хариуцсан нэгж</small>
              <strong>{tender.owner_unit}</strong>
            </article>
            <article className="fact">
              <small>Батлагдсан төсөв</small>
              <strong>{formatMnt(tender.budget_mnt)}</strong>
            </article>
            <article className="fact">
              <small>Техникийн доод оноо</small>
              <strong>{tender.min_technical_score}</strong>
            </article>
            <article className="fact">
              <small>Материал хүлээн авах эцсийн хугацаа</small>
              <strong>{formatDate(tender.due_date)}</strong>
            </article>
          </div>

          <div className="stack" style={{ marginTop: "12px" }}>
            {submissions.map((submission) => (
              <article className="card" key={submission.id}>
                <h3>{submission.organization_name}</h3>
                <div className="bidder-values">
                  <span className="value">
                    <small>Үнийн санал</small>
                    <strong>{formatMnt(submission.proposed_amount_mnt)}</strong>
                  </span>
                  <span className="value">
                    <small>Материал</small>
                    <strong>{submission.documents_complete ? "Бүрэн" : "Дутуу"}</strong>
                  </span>
                  <span className="value">
                    <small>Татварын тодорхойлолт</small>
                    <strong>{submission.tax_compliant ? "Хүчинтэй" : "Хүчингүй"}</strong>
                  </span>
                  <span className="value">
                    <small>Техникийн оноо</small>
                    <strong>{submission.technical_score ?? "Бүртгэгдээгүй"}</strong>
                  </span>
                </div>
                <code className="source">Эх сурвалж: {submission.evidence_reference}</code>
              </article>
            ))}
          </div>
        </section>

        {/* 2. Deterministic rule results ------------------------------------ */}
        <section className="section">
          <div className="section-title">
            <h2>2. Дүрмийн шалгалт</h2>
            <p>
              Эдгээр шалгалтыг программ дээрх баримтаас тооцоолсон. Хариултыг гар аргаар дахин
              шалгаж болно. AI эдгээрийг гаргадаггүй, өөрчилж ч чадахгүй.
            </p>
          </div>

          <div className="card">
            {checks.map((check) => (
              <div className="check" key={check.rule_id}>
                <span className="check-main">
                  <strong>{check.title_mn}</strong>
                  <small>{check.description_mn}</small>
                </span>
                <span className={`badge ${check.result === "attention" ? "attention" : ""}`}>
                  {check.result === "attention"
                    ? `${check.failed} анхаарах`
                    : `${check.passed}/${check.checked} тэнцсэн`}
                </span>
              </div>
            ))}
          </div>

          <div className="stack" style={{ marginTop: "12px" }}>
            {attention.length === 0 ? (
              <p className="empty">Дүрмийн шалгалтаар анхаарах асуудал илрээгүй байна.</p>
            ) : (
              attention.map((finding, index) => (
                <article className="finding" key={`${finding.rule_id}-${index}`}>
                  <p>{finding.message_mn}</p>
                  <code className="source">Эх сурвалж: {finding.source_reference}</code>
                </article>
              ))
            )}
          </div>
        </section>

        {/* 3 and 4. AI draft and the separate human decision ----------------- */}
        <section className="section">
          <DecisionPanel tenderId={Number(id)} />
        </section>

        {/* 5. Decision history ---------------------------------------------- */}
        <section className="section">
          <div className="section-title">
            <h2>4. Шийдвэрийн бүртгэл</h2>
            <p>Төсөл болон батлагдсан шийдвэр тус тусдаа хадгалагдана.</p>
          </div>
          <div className="card">
            {decisions.length === 0 ? (
              <p className="empty">Одоогоор бэлтгэсэн төсөл алга.</p>
            ) : (
              decisions.map((decision) => (
                <div className="audit-item" key={decision.id}>
                  <strong>
                    №{decision.id} · {decisionStatusLabels[decision.status] || decision.status}
                  </strong>
                  <div className="audit-meta">
                    <span>AI сервис: {decision.generated_by}</span>
                    <span>Үүссэн: {formatDateTime(decision.created_at)}</span>
                    <span>Баталсан: {decision.approved_by || "—"}</span>
                    <span>Батлагдсан: {formatDateTime(decision.approved_at)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        {/* 6. Audit trail ---------------------------------------------------- */}
        <section className="section">
          <div className="section-title">
            <h2>5. Аудитын бүртгэл</h2>
            <p>Хэн, хэзээ, юу хийсэн нь бүртгэгдэнэ.</p>
          </div>
          <div className="card">
            {auditEvents.length === 0 ? (
              <p className="empty">Бүртгэл алга.</p>
            ) : (
              auditEvents.map((event) => (
                <div className="audit-item" key={event.id}>
                  <strong>{event.label_mn}</strong>
                  <div className="audit-meta">
                    <span>Гүйцэтгэсэн: {event.actor_label_mn}</span>
                    <span>Эрх: {event.actor_role_label_mn}</span>
                    <span>Хамаарах: {event.target_label_mn}</span>
                    <span>{formatDateTime(event.created_at)}</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="section">
          <div className="notice accent">
            Энэ тендер, оролцогч, тоон мэдээлэл нь зохиомол жишээ. Мөн эрхийн сонголт нь зөвхөн
            үзүүлэнгийн зориулалттай бөгөөд жинхэнэ нэвтрэлт биш.
          </div>
        </section>
      </main>

      <footer className="footer">
        <div className="container footer-inner">
          <span>Organization Brain Starter · Phase 1</span>
          <span>Зохиомол жишээ өгөгдөл</span>
        </div>
      </footer>
    </>
  );
}
