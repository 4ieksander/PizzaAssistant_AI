import React, { useState } from "react";
import SpeechRecognition, { useSpeechRecognition } from "react-speech-recognition";
import axios from "axios";
import "./App.css";

function App() {
    const { transcript, resetTranscript } = useSpeechRecognition();
    const [phone, setPhone] = useState("");
    const [text, setText] = useState(transcript);
    
    const handleInitOrder = async (event) => {
        event.preventDefault(); // Zapobiega odświeżeniu strony
        try {
            const response = await axios.post("http://localhost:8005/init-order", { "phone": phone });
            console.log("Order initialized:", response.data);
        } catch (error) {
            console.error("Error initializing order:", error);
        }
    };
    
    const handleSubmit = async (event) => {
        event.preventDefault(); 
        try {
            const response = await axios.post("http://localhost:8005/", { text });
            console.log("Order submitted:", response.data);
        } catch (error) {
            console.error("Error submitting order:", error);
        }
    };
    
    return (
        <div>
            <h1>Pizza Assistant</h1>
            
            {/* Formularz inicjalizacji zamówienia */}
            <form onSubmit={handleInitOrder}>
                <input
                    type="text"
                    id="phone-input"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="Wpisz numer telefonu"
                />
                <button type="submit">Zadzwoń i zacznij zamówienie</button>
            </form>
            
            {/* Przechwytywanie mowy */}
            <button onClick={SpeechRecognition.startListening}>Mów</button>
            <p>{transcript}</p>
            
            {/* Formularz wysyłania zamówienia */}
            <form onSubmit={handleSubmit}>
                <input
                    type="text"
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    placeholder="Wprowadź treść zamówienia"
                />
                <button type="submit">Wyślij zamówienie</button>
            </form>
        </div>
    );
}

export default App;
