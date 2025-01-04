import React, { useEffect, useState } from "react";
import axios from "axios";
import Button from "@mui/material/Button";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogContentText from "@mui/material/DialogContentText";
import DialogTitle from "@mui/material/DialogTitle";
import CircularProgress from "@mui/material/CircularProgress";
import SpeechRecognition, { useSpeechRecognition } from "react-speech-recognition";

function AnalyzeOrderDialogue({ isOpen, onClose, phone }) {
	const [orderData, setOrderData] = useState(null);
	const [conversationId, setConversationId] = useState(null);
	const [parsedItems, setParsedItems] = useState([]);
	const [pendingItems, setPendingItems] = useState([]);
	const [completedItems, setCompletedItems] = useState([]);
	const [conversationMessage, setConversationMessage] = useState("");
	const [loading, setLoading] = useState(false);
	const { transcript, resetTranscript } = useSpeechRecognition();
	
	useEffect(() => {
		if (isOpen) {
			setLoading(true);
			axios
				.post("http://localhost:8005/orders/init", { phone })
				.then((response) => {
					setOrderData(response.data);
					console.log(response.data);
					setLoading(false);
				})
				.catch((error) => {
					console.error("Error fetching order data:", error);
					setLoading(false);
				});
		}
	}, [isOpen, phone]);
	
	const startConversation = async (orderId, initialText) => {
		try {
			setLoading(true);
			const response = await axios.post("http://localhost:8005/conversation/start", {
				order_id: orderId,
				initial_text: initialText
			});
			console.log("startConversation response:", response.data);
			setConversationId(response.data.conversation_id);
			setConversationMessage(response.data.message);
			setParsedItems(response.data.parsed_items || []);
			setPendingItems(response.data.parsed_items?.filter((it) => it.missing_info?.length > 0) || []);
			setCompletedItems(response.data.parsed_items?.filter((it) => !it.missing_info?.length) || []);
		} catch (err) {
			console.error("Error in startConversation:", err);
		} finally {
			setLoading(false);
		}
	};
	
	const handleContinueConversation = async (userText) => {
		if (!conversationId) return;
		try {
			setLoading(true);
			const response = await axios.post("http://localhost:8005/conversation/continue", {
				conversation_id: conversationId,
				user_text: userText
			});
			console.log("continueConversation response:", response.data);
			// Aktualizujemy stan
			setConversationMessage(response.data.message);
			setPendingItems(response.data.pending_items || []);
			setCompletedItems(response.data.completed_items || []);
		} catch (err) {
			console.error("Error in continueConversation:", err);
		} finally {
			setLoading(false);
		}
	};

	const handleSendTranscript = () => {
		if (!conversationId){
			startConversation(orderData.id, transcript);
		}
		handleContinueConversation(transcript);
		
		resetTranscript();
	};
	
	return (
		<Dialog open={isOpen} onClose={onClose} fullWidth maxWidth="sm">
			<DialogTitle>Order Details</DialogTitle>
			<DialogContent>
				{/* Ładowanie danych */}
				{loading ? (
					<div style={{ display: "flex", justifyContent: "center", alignItems: "center" }}>
						<CircularProgress />
					</div>
				) : orderData ? (
					<div>
						{/* Wyświetlenie danych zamówienia */}
						<h3>Order Summary</h3>
						<p><strong>ID zamówienia:</strong> {orderData.id}</p>
						<p><strong>ID konwersacji</strong> {conversationId || "Brak"}</p>
						<p><strong>Czas rozpoczęcia:</strong> {orderData.order_start_time}</p>
						<p><strong>Numer telefonu:</strong> {phone}</p>
						{/* Transkrypcja */}
						{/* Komunikat z backendu */}
						<p>{conversationMessage}</p>
						
						{/* Wyświetlenie pending i completed */}
						<h4>Pending Items:</h4>
						{pendingItems.map((item, idx) => (
							<p key={idx}>
								Pizza: {item.pizza || "(no name)"} - Missing: {item.missing_info.join(", ")}
							</p>
						))}
						<h4>Completed Items:</h4>
						{completedItems.map((item, idx) => (
							<p key={idx}>
								Pizza: {item.pizza} - OK
							</p>
						))}
						<Button onClick={SpeechRecognition.startListening} variant="contained">
							Zacznij nagrywać
						</Button>
						<Button onClick={resetTranscript} variant="outlined">
							Resetuj transkrypcję
						</Button>
						<Button onClick={handleSendTranscript} variant="contained">
							Wyślij
						</Button>
						<p><em>Transkrypcja: </em> {transcript || "Zacznij mówić aby zobaczyć tutaj transkrypcję..."}</p>
					</div>
				) : (
					<DialogContentText>
						Unable to fetch order data. Please try again.
					</DialogContentText>
				)}
			</DialogContent>
			<DialogActions>
				<Button onClick={onClose} color="primary">
					Zakończ
				</Button>
			</DialogActions>
		</Dialog>
	);
}

export default AnalyzeOrderDialogue;
