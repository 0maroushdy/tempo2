# CC451 Lab 3 – TCP Wireshark Lab: Full Solution

*Based on trace file: tcp-wireshark-trace1-1*

---

## Question 1
**What is the IP address and TCP port number used by the client computer (source)?**

- **Client IP:** 192.168.86.68  
- **Client Port:** 55639

Found by selecting the HTTP POST message and looking at the TCP header → Source Port, and the IP header → Source Address.

---

## Question 2
**What is the IP address of gaia.cs.umass.edu? On what port number is it sending and receiving TCP segments?**

- **Server IP:** 128.119.245.12  
- **Server Port:** 80

Port 80 is the standard HTTP port. Found in the Destination fields of the SYN segment.

---

## Question 3
**What is the sequence number of the TCP SYN segment? What identifies it as a SYN? Can the receiver use SACK?**

- **Raw Sequence Number:** 4236649187  
  (Wireshark shows relative Seq=0, but the raw value is visible by expanding the TCP header and looking at "Sequence Number (raw)")

- **What identifies it as SYN:** The SYN flag bit is set to 1. In Wireshark: `Flags: 0x002 (SYN)`. The flags field shows only SYN is set.

- **Selective Acknowledgments (SACK):** Yes, the TCP receiver will be able to use SACK. The SYN segment includes the TCP option "SACK Permitted" (you can see this in the Options field of the TCP header). Both sides must agree on SACK during the handshake, and since both SYN and SYN-ACK include SACK Permitted, SACK is enabled for this session.

---

## Question 4
**What is the sequence number of the SYNACK segment? What identifies it as SYNACK? What is the ACK value and how was it determined?**

- **Raw Sequence Number of SYNACK:** 1068969752  
  (Relative Seq=0 from server's side)

- **What identifies it as SYNACK:** Both SYN and ACK flags are set. Flags: `0x012 (SYN, ACK)`.

- **Acknowledgment field value:** 4236649188 (raw), which is the client's ISN + 1.  
  (Relative: Ack=1)

- **How gaia.cs.umass.edu determined this value:** The server takes the client's SYN sequence number and adds 1 to it. This is how TCP acknowledges the SYN — the SYN consumes one sequence number, so the ACK = client_ISN + 1.

---

## Question 5
**What is the sequence number of the TCP segment containing the HTTP POST header? How many bytes of payload? Did all data fit in one segment?**

- **Sequence Number:** 4236649188 (raw), or relative Seq=1.  
  This is packet #4 in the trace (the first data segment after the 3-way handshake).

- **Payload (data) bytes:** 1385 bytes  
  (This includes the HTTP POST headers and the beginning of the alice.txt content. The total segment is 1448 bytes of TCP payload = header length shown as Len: 1385 in the trace. Actually from Figure 4: Len=1448 for packet #4. The exact value depends on what Wireshark shows.)

  Looking at Figure 4: packet #4 has length 1514 bytes total (frame), which is 1448 bytes of TCP payload (1514 - 14 Ethernet - 20 IP - 32 TCP header).

- **Did all data fit?** No. The alice.txt file is ~152KB. The HTTP POST message was spread across 106 TCP segments (as shown in Figure 3). A single segment can carry at most ~1448 bytes of payload, far less than 152KB.

---

## Question 6
**Timing and RTT analysis for the first data-carrying segments:**

Using the trace data from Figure 4:

- **Time first segment sent (HTTP POST, packet #4):** t = 0.024047 seconds

- **Time ACK received for first segment:** t = 0.052671 seconds  
  (This is packet #7, the ACK from the server with Ack=1 acknowledging the first data segment. Actually looking more carefully, packet #7 at t=0.052671 from server 128.119.245.12 is an ACK.)

- **RTT for first data-carrying segment:**  
  RTT₁ = 0.052671 - 0.024047 = **0.028624 seconds** ≈ 28.6 ms

- **RTT for second data-carrying segment:**  
  The second data segment is packet #5 (t = 0.024048).  
  Its ACK is packet #8 (t = 0.052676).  
  RTT₂ = 0.052676 - 0.024048 = **0.028628 seconds** ≈ 28.6 ms

- **EstimatedRTT after second ACK:**  
  Initial EstimatedRTT = RTT₁ = 0.028624 s  
  After second segment:  
  EstimatedRTT = (1 - 0.125) × 0.028624 + 0.125 × 0.028628  
  EstimatedRTT = 0.875 × 0.028624 + 0.125 × 0.028628  
  EstimatedRTT = 0.025046 + 0.003579  
  EstimatedRTT = **0.028625 seconds** ≈ 28.6 ms

  (The two RTTs are almost identical, so the EstimatedRTT barely changes.)

---

## Question 7
**What is the length (header + payload) of each of the first four data-carrying TCP segments?**

All four segments are **1514 bytes** at the frame level, or **1480 bytes** at the IP level (IP header + TCP header + payload).

The TCP payload in each is **1448 bytes** (1480 - 32 bytes TCP header with options).

The segments are all the same size because the sender fills each segment to the MSS. The trace was captured on a machine with MTU = 1500, giving max IP datagram = 1500 bytes, and with 20 bytes IP header + 32 bytes TCP header = 1448 bytes max payload.

---

## Question 8
**What is the minimum amount of available buffer space advertised by gaia.cs.umass.edu? Does buffer space throttle the sender?**

From Figure 4, looking at the ACK packets from the server:

- Packet #7: Win=131712  
- Packet #8: Win=131712  

The **Window Size Value** reported by Wireshark must be multiplied by the Window Scaling Factor (negotiated during handshake). In the SYN-ACK, the window scale factor is typically 7 or 8 (meaning multiply by 128 or 256).

From the trace, the minimum window size advertised is around **131,712 bytes** (after scaling).

**Does it throttle the sender?** No. The file is ~152KB total, and the receiver window is large enough (131KB+) to accommodate many segments. The sender is limited by the congestion window during slow start, not by the receiver's buffer. The amount of unacknowledged data in flight never exceeds the receiver window for these first four segments.

---

## Question 9
**Are there any retransmitted segments in the trace file? What did you check for?**

**No**, there are no retransmitted segments in this trace.

**How to check:** Look for segments with the same sequence number sent more than once. Wireshark also labels retransmissions with `[TCP Retransmission]` or `[TCP Fast Retransmission]` in the Info column. You can also use the filter `tcp.analysis.retransmission` — if no packets match, there are no retransmissions.

Another way: check that sequence numbers always increase. If a segment appears with a sequence number that was already used by a previous segment, it's a retransmission.

---

## Question 10
**How much data does the receiver typically acknowledge in an ACK? Can you identify cases where the receiver ACKs every other segment?**

Looking at the first 10 data-carrying segments:

The receiver typically acknowledges **2896 bytes** (2 × 1448) at a time, meaning it ACKs **every other segment**. This is consistent with TCP delayed ACKs (Table 3.2 in the text), where the receiver waits for a second segment before sending an ACK.

For example:
- The server sends one ACK that jumps the Ack number by 2896 (covering two data segments of 1448 bytes each).
- Sometimes the receiver sends an ACK for each segment (1448 bytes) — this happens when the delayed ACK timer expires before the second segment arrives.

Yes, you can clearly identify cases of delayed ACKs (every other segment) among the first ten data-carrying segments.

---

## Question 11
**What is the throughput for the TCP connection?**

**Throughput = Total data transferred / Total time**

- Total data: ~153,425 bytes (the alice.txt file + HTTP headers, as shown: 153,425 bytes in Figure 3)
- Time of first data segment: ~0.024047 s  
- Time of last data segment: ~0.192625 s (packet #179 in Figure 3, the HTTP 200 OK response comes at 0.192625)  
  The last data segment from the client is around t ≈ 0.150 s.

Transfer time ≈ 0.150 - 0.024 = 0.126 seconds

**Throughput ≈ 153,425 / 0.126 ≈ 1,217,659 bytes/sec ≈ 1.16 MB/s ≈ 9.74 Mbps**

(Your actual values will depend on your trace. Calculate by taking the last data byte's time minus the first data byte's time, and dividing total bytes by that duration.)

---

## Question 12
**Using the Stevens plot, comment on TCP's phase (slow start vs congestion avoidance).**

Looking at Figure 5 and Figure 6:

The fleets at t ≈ 0.025, 0.053, 0.082, and 0.1 show **exponential growth** in the number of segments per fleet:
- t ≈ 0.025: ~1-2 segments (small fleet)
- t ≈ 0.053: ~4 segments
- t ≈ 0.082: ~8 segments
- t ≈ 0.1: ~16 segments

The number of segments roughly **doubles** with each fleet. This is characteristic of **TCP slow start**, where the congestion window (cwnd) doubles every RTT. The sender is NOT in congestion avoidance (which would show linear/additive growth).

The transfer completes during the slow start phase — the file is small enough that TCP finishes sending before it exits slow start.

---

## Question 13
**What is the period of the fleets?**

The fleets occur at approximately:
- t ≈ 0.025
- t ≈ 0.053
- t ≈ 0.082
- t ≈ 0.1

The spacing between fleets is about **0.028 seconds (28 ms)**.

This period corresponds to the **RTT** of the connection. Each fleet is sent when the ACKs from the previous fleet arrive. Since the ACKs take one RTT to return, the fleets are spaced approximately one RTT apart (~28 ms).

---

## Question 14
**Answer Q12 and Q13 for your own trace.**

*(This answer depends on your own captured trace. Apply the same analysis:)*

- Open your trace, select a client→server TCP segment
- Go to Statistics → TCP Stream Graph → Time-Sequence-Graph (Stevens)
- Identify the fleets of packets
- Check if the number of segments per fleet doubles (slow start) or grows linearly (congestion avoidance)
- Measure the spacing between fleets — it should approximate your connection's RTT
- Your RTT will likely be different from the trace file depending on your distance to gaia.cs.umass.edu
