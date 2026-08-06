import Link from "next/link";

export default function SiteHeader({ note }) {
  return (
    <header className="site-header">
      <div className="container header-inner">
        <Link href="/" className="brand" aria-label="Нүүр хуудас">
          <span className="brand-mark" aria-hidden="true">
            БТ
          </span>
          <span>
            <strong>Байгууллагын тархи</strong>
            <small>Organization Brain Starter</small>
          </span>
        </Link>
        {note ? (
          <Link href="/" className="header-note">
            {note}
          </Link>
        ) : (
          <span className="header-note">Жишиг систем · зохиомол өгөгдөл</span>
        )}
      </div>
    </header>
  );
}
