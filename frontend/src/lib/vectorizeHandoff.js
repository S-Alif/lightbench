// lets another page pass one image to the vectorizer page (kept in memory only)
let pendingFile = null
export const setVectorizeHandoff = (file) => { pendingFile = file }
export const takeVectorizeHandoff = () => { const file = pendingFile; pendingFile = null; return file }
