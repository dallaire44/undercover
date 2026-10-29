import { useEffect, useState } from "react";
import { listClaims } from "./api";
import { Claim } from "./Claim";
import { Instructions } from "./Instructions";
import { Queue } from "./Queue";
import { useLoad } from "./useLoad";

function useHash() {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const update = () => {
      setHash(window.location.hash);
    };
    window.addEventListener("hashchange", update);
    return () => {
      window.removeEventListener("hashchange", update);
    };
  }, []);
  return hash;
}

function QueuePage() {
  const { data: claims, failed, reload } = useLoad(listClaims, () => true);
  if (failed) return <p>The claims could not be loaded.</p>;
  if (!claims) return <p className="muted">Loading</p>;
  return <Queue claims={claims} onWork={() => void reload()} />;
}

function Page({ hash }: Readonly<{ hash: string }>) {
  const claimId = /^#\/claims\/(.+)$/.exec(hash)?.[1];
  if (claimId) return <Claim key={claimId} claimId={claimId} />;
  return hash === "#/instructions" ? <Instructions /> : <QueuePage />;
}

export function App() {
  const hash = useHash();
  return (
    <>
      <header>
        <a href="#/" className="brand">
          UnderCover
        </a>
        <span className="tagline">Every claim, read closely.</span>
        <nav>
          <a href="#/">Queue</a>
          <a href="#/instructions">Agent instructions</a>
        </nav>
      </header>
      <main>
        <Page hash={hash} />
      </main>
    </>
  );
}
