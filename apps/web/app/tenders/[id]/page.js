import Link from "next/link";
import { notFound } from "next/navigation";

import DecisionPanel from "../../../components/DecisionPanel";
import { getTender } from "../../../lib/api";

export const dynamic = "force-dynamic";

function formatMnt(value) {
  return `${new Intl.NumberFormat("mn-MN").format(Number(value))} ₮`;
}

export default async function TenderPage({ params }) {
  const { id } = await params;
  let data;

  try {
    data = await getTender(id);
  } catch {
    notFound();
  }

  return (
    <main>
      <header className="site-header">
        <div className="container header-inner">
          <Link href="/" className="brand">
            <span className="brand-mark">БТ</span>
            <span>
              <strong>Байгууллагын тархи</strong>
              <small>Organization Brain Starter</small>
            </span>
          </Link>
          <Link href="/" className="text-link">← Нүүр хуудас</Link>
        </div>
      </header>

      <section className="detail-hero">
        <div className="container">
          <span className="eyebrow">{data.tender.code}</span>
          <div className="detail-title-row">
            <div>
              <h1>{data.tender.title_mn}</h1>
              <p>{data.tender.purpose_mn}</p>
            </div>
            <span className="stage-badge large">Хүний хяналт</span>
          </div>
        </div>
      </section>

      <section className="container detail-summary-grid">
        <article className="summary-card">
          <small>Хариуцсан нэгж</small>
          <strong>{data.tender.owner_unit}</strong>
        </article>
        <article className="summary-card">
          <small>Батлагдсан төсөв</small>
          <strong>{formatMnt(data.tender.budget_mnt)}</strong>
        </article>
        <article className="summary-card">
          <small>Материал</small>
          <strong>{data.submissions.length} оролцогч</strong>
        </article>
        <article className="summary-card attention">
          <small>Анхаарах асуудал</small>
          <strong>{data.findings.filter((item) => item.severity === "attention").length}</strong>
        </article>
      </section>

      <section className="section container">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Бүтэцтэй харьцуулалт</span>
            <h2>Оролцогчдын мэдээлэл</h2>
          </div>
          <p>Энд дүрмийн болон тоон мэдээллийг AI-аас тусад нь харуулж байна.</p>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Оролцогч</th>
                <th>Үнийн санал</th>
                <th>Материал</th>
                <th>Татвар</th>
                <th>Техникийн оноо</th>
              </tr>
            </thead>
            <tbody>
              {data.submissions.map((submission) => (
                <tr key={submission.id}>
                  <td><strong>{submission.organization_name}</strong></td>
                  <td>{formatMnt(submission.proposed_amount_mnt)}</td>
                  <td>
                    <span className={submission.documents_complete ? "check yes" : "check no"}>
                      {submission.documents_complete ? "Бүрэн" : "Дутуу"}
                    </span>
                  </td>
                  <td>
                    <span className={submission.tax_compliant ? "check yes" : "check no"}>
                      {submission.tax_compliant ? "Хүчинтэй" : "Шалгах"}
                    </span>
                  </td>
                  <td>{submission.technical_score}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="section soft-section">
        <div className="container two-column-detail">
          <div>
            <div className="section-heading compact-heading">
              <div>
                <span className="eyebrow">Дүрмийн шалгалт</span>
                <h2>Илэрсэн асуудал</h2>
              </div>
            </div>

            <div className="finding-list">
              {data.findings.map((finding) => (
                <article className={`finding ${finding.severity}`} key={finding.id}>
                  <div className="finding-topline">
                    <span>{finding.organization_name || "Нийт тендер"}</span>
                    <small>{finding.category}</small>
                  </div>
                  <p>{finding.message_mn}</p>
                  <code>{finding.source_reference}</code>
                </article>
              ))}
            </div>
          </div>

          <aside className="control-card">
            <span className="card-kicker">Хяналтын хил</span>
            <h3>AI энд юу хийж болохгүй вэ?</h3>
            <ul>
              <li>Ялагчийг автоматаар сонгохгүй</li>
              <li>Нууц оноо үүсгэхгүй</li>
              <li>Баримт зохиохгүй</li>
              <li>Хүний эрхгүйгээр батлахгүй</li>
            </ul>
          </aside>
        </div>
      </section>

      <section className="section container">
        <DecisionPanel tenderId={Number(id)} />
      </section>

      <footer className="footer">
        <div className="container footer-inner">
          <span>Fictional demonstration data</span>
          <span>AI-assisted, human-controlled.</span>
        </div>
      </footer>
    </main>
  );
}
