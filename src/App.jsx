import React, { useState } from "react";
import axios from "axios";
import "./App.css";
import AnalyzeOrderDialogue from "./components/AnalyzeOrderDialogue";

function App() {
    const [phone, setPhone] = useState("");
    const [isDialogOpen, setIsDialogOpen] = useState(false);
    
    const handleInitOrder = async (event) => {
        await setPhone(phone)
        event.preventDefault();
        setIsDialogOpen(true); // Otwórz dialog
    };
    
    const closeDialog = () => {
        setIsDialogOpen(false);
    };
    
    return (
        <div>
            <h1>Pizza Assistant</h1>
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
            
            {/* Dialog */}
            <AnalyzeOrderDialogue isOpen={isDialogOpen} onClose={closeDialog} phone={phone}/>
        </div>
    );
}

export default App;
