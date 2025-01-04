import React, { useEffect, useState } from "react";
import axios from "axios";

function OrderSummaryView({ orderId }) {
	const [summary, setSummary] = useState(null);
	const [transcriptions, setTranscriptions] = useState([]);
	const [loading, setLoading] = useState(false);
	const [error, setError] = useState("");
	
	const fetchSummary = async () => {
		if (!orderId) return;
		setLoading(true);
		setError("");
		try {
			const response = await axios.get(`http://localhost:8005/orders/summary/${orderId}`);
			setSummary(response.data);
			console.log("Summary response:", response.data);
		} catch (err) {
			console.error("Error fetching summary:", err);
			setError("Nie udało się pobrać podsumowania zamówienia.");
		} finally {
			setLoading(false);
		}
	};
	
	const fetchTranscriptHistory = async () => {
		if (!orderId) return;
		setLoading(true);
		setError("");
		try {
			const response = await axios.get(`http://localhost:8005/orders/transcript/${orderId}`);
			setTranscriptions(response.data);
			console.log("Transcript history response:", response.data);
		} catch (err) {
			console.error("Error fetching transcript history:", err);
			setError("Nie udało się pobrać historii transkrypcji.");
		} finally {
			setLoading(false);
		}}
	
		
		useEffect(() => {
			fetchSummary();
			fetchTranscriptHistory();
		}, [orderId])
		;
		if (loading) {
			return <div>Ładowanie podsumowania...</div>;
		}
		if (error) {
			return <div style={{color: "red"}}>{error}</div>;
		}
		if (!summary) {
			return <div>Brak danych o podsumowaniu.</div>;
		}
		
		return (
			<div style={{marginTop: "20px"}}>
				<h3>Podsumowanie zamówienia #{summary.order_id}</h3>
				{summary.items.map((item, idx) => (
					<div key={idx} style={{border: "1px solid #ccc", marginBottom: "10px", padding: "10px"}}>
						<h4>{item.pizza_name}</h4>
						<p>Ciasto: {item.dough_desc}</p>
						<p>
							Cena za sztukę: {item.price_each}, Ilość: {item.quantity},
							Koszt pozycji: {item.cost}
						</p>
						<p>Składniki:</p>
						<ul>
							{item.ingredients.map((ing, i2) => (
								<li key={i2}>{ing}</li>
							))}
						</ul>
					</div>
				))}
				<h4>Łączny koszt: {summary.total_cost}</h4>
				<h5>Historia transkrypcji:</h5>
				{transcriptions.items && transcriptions.items.length > 0 ? (
					<ul>
						{transcriptions.items.map((transcription, index) => (
							<li key={index}>
								<p><strong>Transkrypcja:</strong> {transcription.content}</p>
								<p><strong>Parsed:</strong> {transcription.parsed}</p>
								<p><strong>Updated rows:</strong> {transcription.updated_slots }</p>
							</li>
						))}
					</ul>
				) : (
					<p>Brak historii transkrypcji</p>
					)}
				
				</div>
		);
	};

export default OrderSummaryView;