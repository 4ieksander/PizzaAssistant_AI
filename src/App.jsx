import React, { useState } from "react";
import SpeechRecognition, { useSpeechRecognition } from "react-speech-recognition";
import axios from "axios";

function App() {
  const [order, setOrder] = useState("");
  const { transcript, resetTranscript } = useSpeechRecognition();
  
  const handleSubmit = async () => {
    const response = await axios.post("http://localhost:8005/menu/test", { text: transcript });
    console.log(response.data);
  };
  
  return (
      <div>
        <h1>Pizza Assistant</h1>
        <button onClick={SpeechRecognition.startListening}>Mów</button>
        <p>{transcript}</p>
        <button onClick={handleSubmit}>Wyślij zamówienie</button>
      </div>
  );
}

export default App;
