import { useEffect, useState } from "react";

interface Photo {
  id: string;
  original_filename: string;
  stored_filename: string;
  file_size: number;
  uploaded_at: string;
  width: number | null;
  height: number | null;
}

function App() {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadPhotos() {
      try {
        const response = await fetch("/photos", { signal: controller.signal });
        if (!response.ok) {
          throw new Error("Unable to load your photos.");
        }

        const result = (await response.json()) as Photo[];
        setPhotos(result);
      } catch (requestError) {
        if (requestError instanceof DOMException && requestError.name === "AbortError") {
          return;
        }

        setError("Memora could not load your photos. Make sure the backend is running.");
      } finally {
        if (!controller.signal.aborted) {
          setIsLoading(false);
        }
      }
    }

    void loadPhotos();
    return () => controller.abort();
  }, []);

  return (
    <main className="page-shell">
      <header className="page-header">
        <p className="eyebrow">Private by design</p>
        <h1>Memora</h1>
        <p className="subtitle">Your photos, stored and viewed locally.</p>
      </header>

      {isLoading && <p className="status">Loading your photos…</p>}

      {!isLoading && error && (
        <p className="status status-error" role="alert">
          {error}
        </p>
      )}

      {!isLoading && !error && photos.length === 0 && (
        <p className="status">No photos yet.</p>
      )}

      {!isLoading && !error && photos.length > 0 && (
        <section className="photo-grid" aria-label="Photo gallery">
          {photos.map((photo) => (
            <figure className="photo-card" key={photo.id}>
              <img
                src={`/photos/${encodeURIComponent(photo.id)}/file`}
                alt={photo.original_filename}
                loading="lazy"
              />
              <figcaption title={photo.original_filename}>
                {photo.original_filename}
              </figcaption>
            </figure>
          ))}
        </section>
      )}
    </main>
  );
}

export default App;
