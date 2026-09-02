const apiKey = localStorage.getItem("dinnercue_omdb_api_key") || "";

async function fetchMovie(title = "Tenet") {
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

        console.log(omdbData);
        return omdbData;
    } catch (error) {
        console.error("Error fetching movie:", error);
        return null;
    }
}

fetchMovie();
