import Link from "next/link";

import SiteHeader from "../components/SiteHeader";
import { getOverview } from "../lib/api";

export const dynamic = "force-dynamic";

const stageLabels = {
  registration: "Бүртгэл",
  rule_check: "Дүрмийн шалгалт",
  human_review: "Хүний хяналт",
  approved: "Батлагдсан",
};

function formatMnt(value) {
  return `${new Intl.NumberFormat("mn-MN").format(Number(value))} ₮`;
}

export default async function HomePage() {
  let data = null;

  try {
    data = await getOverview();
  } catch {
    data = null;
  }

  const metrics = data?.metrics ?? {};
  const tenders = data?.tenders ?? [];
  const steps = data?.workflow_steps ?? [];

  return (
    <>
      <SiteHeader />

      <main className="container page">
        <div className="lede">
          <h1>AI шийдвэр гаргахгүй. Хүний шийдвэрийг илүү баримттай болгоно.</h1>
          <p>
            Батлагдсан мэдээлэл, тодорхой дүрэм, хүний хариуцлагыг нэг ажлын урсгалд холбосон
            энгийн жишиг систем.
          </p>
        </div>

        {!data ? (
          <div className="notice error section" role="alert">
            Мэдээллийн сангийн үйлчилгээ хариу өгөхгүй байна. <code>docker compose up --build</code>{" "}
            ажиллаж дууссаны дараа энэ хуудсыг дахин ачаална уу.
          </div>
        ) : null}

        <section className="section" aria-label="Товч үзүүлэлт">
          <div className="metric-grid">
            <article className="metric">
              <span>Идэвхтэй ажлын урсгал</span>
              <strong>{metrics.active_workflows ?? "—"}</strong>
            </article>
            <article className="metric">
              <span>Хүний хяналт хүлээж буй</span>
              <strong>{metrics.waiting_review ?? "—"}</strong>
            </article>
            <article className="metric">
              <span>Батлагдсан</span>
              <strong>{metrics.approved_workflows ?? "—"}</strong>
            </article>
          </div>
        </section>

        <section className="section">
          <div className="section-title">
            <h2>Ажлын урсгал</h2>
            <p>Нэг бодит процессыг эхнээс нь дуустал ойлгомжтой болгоно.</p>
          </div>
          <div className="steps">
            {steps.map((step, index) => (
              <div className="step" key={step}>
                <span>{index + 1}</span>
                {step}
              </div>
            ))}
            {steps.length === 0 ? <p className="empty">Мэдээлэл алга.</p> : null}
          </div>
        </section>

        <section className="section">
          <div className="section-title">
            <h2>Тендерийн үнэлгээ</h2>
            <p>Систем ялагчийг сонгохгүй. Баримт, дүрмийн шалгалт, анхаарах асуудлыг цэгцэлж өгнө.</p>
          </div>

          <div className="rows">
            {tenders.map((tender) => (
              <Link className="row" href={`/tenders/${tender.id}`} key={tender.id}>
                <div className="row-main">
                  <h3>{tender.title_mn}</h3>
                  <small>
                    {tender.code} · {tender.owner_unit}
                  </small>
                </div>
                <div className="row-side">
                  <span className="value">
                    <small>Төсөв</small>
                    <strong>{formatMnt(tender.budget_mnt)}</strong>
                  </span>
                  <span className="value">
                    <small>Оролцогч</small>
                    <strong>{tender.submission_count}</strong>
                  </span>
                  <span className="value">
                    <small>Анхаарах</small>
                    <strong>{tender.attention_count}</strong>
                  </span>
                  <span className={`badge ${tender.stage === "approved" ? "" : "quiet"}`}>
                    {stageLabels[tender.stage] || tender.stage}
                  </span>
                </div>
              </Link>
            ))}
            {data && tenders.length === 0 ? (
              <p className="empty">Одоогоор бүртгэлтэй ажлын урсгал алга.</p>
            ) : null}
          </div>
        </section>

        <section className="section">
          <div className="notice accent">
            Энэ хуудсан дээрх бүх байгууллага, тендер, оролцогч, тоон мэдээлэл нь зохиомол жишээ
            бөгөөд албан ёсны шийдвэрт ашиглахгүй.
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
