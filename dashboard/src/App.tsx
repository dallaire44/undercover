import { ClaimPage } from "./ClaimPage";
import { Instructions } from "./Instructions";
import { ModeSwitch } from "./ModeSwitch";
import { Queue } from "./Queue";
import { useRoute } from "./route";
import type { Route } from "./route";

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
          <ModeSwitch
            label="Dark mode"
            attribute="theme"
            on="dark"
            off="light"
            storageKey="undercover-theme"
          />
          <ModeSwitch
            label="Color-blind mode"
            attribute="colors"
            on="color-blind"
            off="brand"
            storageKey="undercover-colors"
          />
        </nav>
      </header>
      <main>
        <Page route={route} />
      </main>
    </>
  );
}
