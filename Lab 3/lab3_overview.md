# CC451 Lab 3 – Wireshark TCP Lab (Overview)

## What This Lab Is About

You upload a file (alice.txt) to a server and capture the TCP traffic with Wireshark. Then you analyze the TCP segments to understand how TCP works in practice: connection setup, data transfer, acknowledgments, flow control, and congestion control.

## How to Run the Lab

1. Download alice.txt from: `http://gaia.cs.umass.edu/wireshark-labs/alice.txt`
2. Open: `http://gaia.cs.umass.edu/wireshark-labs/TCP-wireshark-file1.html`
3. Click Browse, select alice.txt — **don't upload yet**
4. Start Wireshark, begin capturing packets
5. Go back to the browser, click "Upload alice.txt file"
6. Wait for the "Congratulations" message
7. Stop Wireshark capture
8. Use filter `tcp` to see only TCP segments

**Alternative:** Download the pre-made trace from:  
`http://gaia.cs.umass.edu/wireshark-labs/wireshark-traces-8.1.zip`  
Open file `tcp-wireshark-trace1-1` in Wireshark.

## Key Definitions

**TCP (Transmission Control Protocol):** Reliable, connection-oriented transport protocol. Guarantees delivery, order, and no duplicates.

**Three-Way Handshake:** How TCP opens a connection:
- Client sends SYN (synchronize)
- Server replies with SYN-ACK
- Client sends ACK → connection established

**Sequence Number:** A number attached to each TCP segment identifying the first byte of data in that segment. Starts with a random ISN (Initial Sequence Number).

**Acknowledgment Number:** Tells the sender "I've received everything up to this byte, send me the next one." It's the next expected byte number.

**SYN flag:** Set to 1 to initiate a connection. The SYN segment carries no data but uses one sequence number.

**SACK (Selective Acknowledgment):** An option that lets the receiver tell the sender exactly which blocks of data it received, so only missing segments get retransmitted.

**RTT (Round-Trip Time):** Time between sending a segment and receiving its ACK.

**EstimatedRTT:** A smoothed average of RTT samples:  
`EstimatedRTT = (1 - α) × EstimatedRTT + α × SampleRTT`  
where α = 0.125

**MSS (Maximum Segment Size):** Largest chunk of data TCP will put in one segment. Typically ~1448 bytes (1500 MTU - 20 IP header - 20 TCP header - 12 options).

**Window Size (rwnd):** How much buffer space the receiver has available. Advertised in each ACK. Sender must not send more unACKed data than this value.

**Flow Control:** Mechanism where the receiver limits the sender's rate using the window size field, preventing buffer overflow at the receiver.

**Congestion Control — Slow Start:** TCP starts by sending 1 segment, then doubles the sending rate (1, 2, 4, 8...) each RTT until it hits a threshold or detects loss.

**Congestion Control — Congestion Avoidance:** After reaching the threshold (ssthresh), TCP increases the window by ~1 MSS per RTT (linear growth instead of exponential).

**Throughput:** Total bytes transferred / total time. Measures how fast data actually moves.

**Retransmission:** Re-sending a segment because it was lost or its ACK was lost. Detected by duplicate ACKs or timeout.

## Wireshark Tips for This Lab

- Filter: type `tcp` in the filter bar
- To see the Stevens plot: select a TCP segment → Statistics → TCP Stream Graph → Time-Sequence-Graph (Stevens)
- To see RTT: Statistics → TCP Stream Graph → Round Trip Time Graph
- Look at "Seq" and "Ack" columns in the packet list
- Expand TCP header in the middle pane to see flags, window size, options
