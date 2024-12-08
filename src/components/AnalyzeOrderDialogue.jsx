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
	const [loading, setLoading] = useState(false);
	const { transcript, resetTranscript } = useSpeechRecognition();
	
	useEffect(() => {
		if (isOpen) {
			setLoading(true);
			axios
				.post("http://localhost:8005/init-order", { phone })
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
						<p><strong>Order ID:</strong> {orderData.id}</p>
						<p><strong>Start Time:</strong> {orderData.order_start_time}</p>
						<p><strong>Client Phone:</strong> {phone}</p>
						{/* Transkrypcja */}
						<h4>Speech to Text</h4>
						<p><em>Transcript:</em> {transcript || "Start speaking to see transcript here..."}</p>
						<Button onClick={SpeechRecognition.startListening} variant="contained">
							Start Listening
						</Button>
						<Button onClick={resetTranscript} variant="outlined" style={{ marginLeft: "10px" }}>
							Reset
						</Button>
					</div>
				) : (
					<DialogContentText>
						Unable to fetch order data. Please try again.
					</DialogContentText>
				)}
			</DialogContent>
			<DialogActions>
				<Button onClick={onClose} color="primary">
					Close
				</Button>
			</DialogActions>
		</Dialog>
	);
}

export default AnalyzeOrderDialogue;
