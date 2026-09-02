const apiKey = localStorage.getItem("dinnercue_omdb_api_key") || "";

async function fetchMovieData(title = "Tenet") {
  if (!apiKey) {
    console.warn("Add an OMDb API key to localStorage as dinnercue_omdb_api_key before running this demo.");
    return null;
  }

  const omdbUrl = `https://www.omdbapi.com/?apikey=${apiKey}&t=${encodeURIComponent(title)}`;

  try {
    const omdbResponse = await fetch(omdbUrl);
    const omdbData = await omdbResponse.json();

    if (omdbData.Response === "False") {
      console.warn(`No movie found for "${title}".`);
      return null;
    }

    const movie = {
      title: omdbData.Title,
      year: omdbData.Year,
      plot: omdbData.Plot,
      poster: omdbData.Poster,
      imdbRating: omdbData.imdbRating,
    };

    console.log("Movie data:", movie);
    return movie;
  } catch (error) {
    console.error("Error fetching movie data:", error);
    return null;
  }
}

fetchMovieData();
