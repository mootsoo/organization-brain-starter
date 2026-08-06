import Link from "next/link";

import SiteHeader from "../components/SiteHeader";

export default function NotFound() {
  return (
    <>
      <SiteHeader />
      <main className="container page">
        <div className="lede">
          <h1>Хуудас олдсонгүй</h1>
          <p>
            Хайсан ажлын урсгал байхгүй байна, эсвэл мэдээллийн сангийн үйлчилгээ хариу өгөхгүй
            байна.
          </p>
          <p style={{ marginTop: "16px" }}>
            <Link className="button" href="/">
              Нүүр хуудас руу буцах
            </Link>
          </p>
        </div>
      </main>
    </>
  );
}
