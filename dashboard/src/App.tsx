import { ClaimPage } from "./ClaimPage";
import { Queue } from "./Queue";
import { useRoute } from "./route";

export function App() {
  const route = useRoute();
  return (
    <>
      <header className="top">
        <a href="#/" className="brand">
          <h1>UnderCover</h1>
        </a>
        <p className="tagline">
          Every claim decided, and every decision explained.
        </p>
      </header>
      <main>
        {route.page === "claim" ? (
          <ClaimPage key={route.id} id={route.id} />
        ) : (
          <Queue />
        )}
      </main>
    </>
  );
}
