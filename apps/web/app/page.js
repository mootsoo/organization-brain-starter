import Link from "next/link";

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
  let data;
  let apiError = false;

  try {
    data = await getOverview();
  } catch {
    apiError = true;
    data = {
      metrics: {
        active_workflows: 0,
        waiting_review: 0,
        approved_workflows: 0,
      },
      workflow_steps: [],
      tenders: [],
    };
  }

  return (
    <main>
      <header className="site-header">
        <div className="container header-inner">
          <Link href="/" className="brand" aria-label="Нүүр хуудас">
            <span className="brand-mark">БТ</span>
            <span>
              <strong>Байгууллагын тархи</strong>
              <small>Organization Brain Starter</small>
            </span>
          </Link>
          <span className="status-pill">Нээлттэй жишиг систем</span>
        </div>
      </header>

      <section className="hero">
        <div className="container hero-grid">
          <div>
            <span className="eyebrow">Энгийн · Хяналттай · Ажилладаг</span>
            <h1>AI шийдвэр гаргахгүй. Хүний шийдвэрийг илүү баримттай болгоно.</h1>
            <p className="hero-copy">
              Баталгаатай өгөгдөл, тодорхой дүрэм, ажлын урсгал, AI-аар бэлтгэсэн төсөл,
              хүний баталгаажуулалтыг нэг ойлгомжтой системд холбоно.
            </p>
            <div className="hero-actions">
              <Link href="/tenders/1" className="button primary">
                Тендерийн жишээ үзэх
              </Link>
              <a href="#how-it-works" className="button secondary">
                Хэрхэн ажиллах вэ?
              </a>
            </div>
          </div>

          <aside className="principle-card">
            <span className="card-kicker">Үндсэн зарчим</span>
            <blockquote>
              “Хиймэл оюун ухаан байгууллагын тархи биш. Баталгаатай мэдээлэл,
              дүрэм, шийдвэрийн түүх нь тархи юм.”
            </blockquote>
            <p>AI бол зөвхөн хяналттай туслах.</p>
          </aside>
        </div>
      </section>

      <section className="container metric-grid" aria-label="Товч үзүүлэлт">
        <article className="metric-card">
          <span>Идэвхтэй урсгал</span>
          <strong>{data.metrics.active_workflows}</strong>
          <small>Одоо ажиллаж байгаа процесс</small>
        </article>
        <article className="metric-card">
          <span>Хүний хяналт хүлээж буй</span>
          <strong>{data.metrics.waiting_review}</strong>
          <small>AI өөрөө батлахгүй</small>
        </article>
        <article className="metric-card">
          <span>Батлагдсан</span>
          <strong>{data.metrics.approved_workflows}</strong>
          <small>Аудитын мөртэй шийдвэр</small>
        </article>
      </section>

      {apiError ? (
        <section className="container">
          <div className="notice error">
            API холбогдоогүй байна. `docker compose up --build` командыг ажиллуулсны дараа
            жишээ мэдээлэл энд харагдана.
          </div>
        </section>
      ) : null}

      <section id="how-it-works" className="section container">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Нэг ажлын урсгал</span>
            <h2>Удирдлага ойлгоход таван алхам хангалттай</h2>
          </div>
          <p>
            Том платформоос эхлэхгүй. Нэг бодит процессийг төгсгөл хүртэл нь ойлгомжтой болгоно.
          </p>
        </div>

        <div className="steps">
          {data.workflow_steps.map((step, index) => (
            <div className="step" key={step}>
              <span>{index + 1}</span>
              <strong>{step}</strong>
            </div>
          ))}
        </div>
      </section>

      <section className="section soft-section">
        <div className="container">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Ажиллаж буй жишээ</span>
              <h2>AI-assisted tender evaluation</h2>
            </div>
            <p>
              Систем ялагч сонгохгүй. Материал, дүрмийн шалгалт, анхаарах асуудал,
              дүгнэлтийн төслийг нэг дор харуулна.
            </p>
          </div>

          <div className="workflow-list">
            {data.tenders.map((tender) => (
              <Link className="workflow-row" href={`/tenders/${tender.id}`} key={tender.id}>
                <div>
                  <span className="workflow-code">{tender.code}</span>
                  <h3>{tender.title_mn}</h3>
                  <p>{tender.owner_unit}</p>
                </div>
                <div className="workflow-stats">
                  <span>
                    <small>Төсөв</small>
                    {formatMnt(tender.budget_mnt)}
                  </span>
                  <span>
                    <small>Оролцогч</small>
                    {tender.submission_count}
                  </span>
                  <span>
                    <small>Анхаарах</small>
                    {tender.attention_count}
                  </span>
                  <span className="stage-badge">{stageLabels[tender.stage] || tender.stage}</span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="section container">
        <div className="three-column">
          <article className="info-card">
            <span>01</span>
            <h3>Өгөгдлөө эхлээд цэгцэл</h3>
            <p>AI-д бүх системийн эрх өгөхгүй. Программ шаардлагатай мэдээллийг сонгож өгнө.</p>
          </article>
          <article className="info-card">
            <span>02</span>
            <h3>Дүрэм ба AI-г ялга</h3>
            <p>Бүрдэл, төсөв зэрэг шалгалтыг код хийж, AI зөвхөн тайлбарын төсөл бэлтгэнэ.</p>
          </article>
          <article className="info-card">
            <span>03</span>
            <h3>Хүний эрхийг хадгал</h3>
            <p>Эрх бүхий хүн хянаж батлаагүй бол албан ёсны шийдвэр болохгүй.</p>
          </article>
        </div>
      </section>

      <footer className="footer">
        <div className="container footer-inner">
          <span>Organization Brain Starter</span>
          <span>Simple systems before complicated AI.</span>
        </div>
      </footer>
    </main>
  );
}
