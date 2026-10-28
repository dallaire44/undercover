import { ClaimPage } from "./ClaimPage";
import { Instructions } from "./Instructions";
import { Queue } from "./Queue";
import { useRoute } from "./route";
import type { Route } from "./route";
import { ThemeSwitch } from "./ThemeSwitch";

function Page({ route }: Readonly<{ route: Route }>) {
  switch (route.page) {
    case "claim":
      return <ClaimPage key={route.id} id={route.id} />;
    case "instructions":
      return <Instructions />;
    default:
      return <Queue />;
  }
}

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
        <nav>
          <a href="#/instructions">Agent instructions</a>
          <ThemeSwitch />
        </nav>
      </header>
      <main>
        <Page route={route} />
      </main>
    </>
  );
}
