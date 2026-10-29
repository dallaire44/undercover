import { useEffect, useState } from "react";
import { listClaims } from "./api";
import { Claim } from "./Claim";
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
  const { data: claims, failed } = useLoad(listClaims);
  if (failed) return <p>The claims could not be loaded.</p>;
  if (!claims) return <p className="muted">Loading</p>;
  return <Queue claims={claims} />;
}

export function App() {
  const claimId = /^#\/claims\/(.+)$/.exec(useHash())?.[1];
  return (
    <>
      <header>
        <a href="#/" className="brand">
          UnderCover
        </a>
        <span className="tagline">Every claim, read closely.</span>
      </header>
      <main>{claimId ? <Claim claimId={claimId} /> : <QueuePage />}</main>
    </>
  );
}
