# **VentOptimizer: Project Master Context & Mega-Prompt**

**Version:** 2.4 (Includes PC/VC Modes, Dynamic Recruitment, Permissive Hypercapnia)

**Purpose:** This document contains the complete context, clinical logic, physics explanations, and source code for the VentOptimizer project. Use this to inform any AI or developer about the exact state of the project.

## **1\. Project Overview**

VentOptimizer is a "White-Box" Decision Support Tool for Mechanical Ventilation. It aims to minimize Ventilator-Induced Lung Injury (VILI) by finding the optimal balance between lung protection (low energy transfer) and metabolic need (gas exchange).

**The Optimization Method (Grid Search):**

Instead of using opaque AI/Machine Learning, the tool uses a brute-force Grid Search. It generates thousands of combinations of ventilator settings (VT, RR, PEEP, Pinsp), predicts the physiological outcome for each, filters out unsafe options using Boolean constraints, and selects the setting with the lowest **Mechanical Power**.

## **2\. Clinical Logic & Physics (The "Why" and "How")**

### **2.1 Mechanical Power (The Cost Function)**

We optimize for Mechanical Power (MP), representing the Joules per minute of energy transferred to the lungs.

* **Equation (Gattinoni):** ![][image1]  
* **VT vs. RR impact:** Adjusting Tidal Volume (VT) has an *exponential (squared)* impact on power because higher volume inherently requires higher pressure. Respiratory Rate (RR) only has a *linear* impact. Therefore, the optimizer naturally favors higher RR and lower VT.

### **2.2 Dynamic Recruitment (How PEEP works)**

Initially, PEEP strictly increased Mechanical Power by adding to peak pressures. However, clinical reality dictates that in recruitable lungs, PEEP improves compliance.

* **The Logic:** We use the Recruitment-to-Inflation (R/I) Index.  
  * If **R/I \> 0.5 (Recruitable):** Increasing PEEP opens alveoli, improving Static Compliance (![][image2]). This lowers Driving Pressure (![][image3]), which can actually *reduce* total Mechanical Power.  
  * If **R/I \< 0.5 (Non-Recruitable):** Increasing PEEP causes overdistension, worsening ![][image2] and increasing Mechanical Power.  
* **Math:** ![][image4]

### **2.3 Auto-PEEP Avoidance (Time Constants)**

To protect Obstructive/COPD patients, the tool calculates the Time Constant (![][image5]) to ensure the lung has enough time to exhale completely.

* **Math:** ![][image6].  
* **Rule:** The Expiratory Time (![][image7]) must be ![][image8]. This guarantees 95% lung emptying. If a setting's RR is too high, making ![][image7] too short, the setting is rejected.

### **2.4 Volume Control (VC) vs. Pressure Control (PC)**

* **VC Mode:** The user sets Tidal Volume (VT). The model predicts the resulting Plateau Pressure (![][image9]) and rejects settings where ![][image10].  
* **PC Mode:** Predicting decelerating flow in PC is computationally heavy and noisy. Instead, we use Ohm's Law. The user sets Inspiratory Pressure (![][image11]). The model predicts the resulting Volume (![][image12]). It rejects settings causing Volutrauma (![][image13] ml/kg). The PC MP equation bypasses flow entirely.

### **2.5 Permissive Hypercapnia & Gas Exchange**

To prevent acidosis, the tool uses the Henderson-Hasselbalch equation to predict pH based on alveolar ventilation.

* **Standard:** Rejects settings resulting in pH \< 7.30.  
* **Permissive Mode:** Lowers the floor to pH \> 7.20. This allows the optimizer to drop RR and VT significantly, saving massive amounts of Mechanical Power at the cost of elevated CO2.

### **2.6 Determining Baseline Plateau Pressure (![][image14])**

The tool *requires* a measured baseline ![][image14] (obtained via an inspiratory hold on the patient). Without this, the tool cannot calculate the baseline Static Compliance (![][image2]), which serves as the foundational variable for all future predictions.

## **3\. Project Challenges & Future Roadmap**

1. **The "ABG Lag":** Optimization currently relies on ![][image15] from blood gases. Waiting 30-60 mins for results limits real-time utility. *Solution: Integrate End-Tidal CO2 (EtCO2) as a real-time proxy.*  
2. **Math vs. Biology:** The model largely assumes linear compliance. Real lungs have inflection points. *Solution: Automated data entry from ventilator hold maneuvers to map the specific compliance curve.*  
3. **Validation:** ARDS heterogeneity makes clinical trials hard. *Solution: Retrospective "Shadow Testing" using the MIMIC-III ICU database to compare the tool's suggestions against historic clinical decisions.*

## **4\. Source Code 1: Web Application (HTML/JS v2.4)**

This is the offline, mobile-friendly clinical prototype featuring both VC and PC modes.

\<\!DOCTYPE html\>  
\<html lang="en"\>  
\<head\>  
    \<meta charset="UTF-8"\>  
    \<meta name="viewport" content="width=device-width, initial-scale=1.0"\>  
    \<title\>VentOptimizer v2.4 (PC Mode Support)\</title\>  
    \<script src="\[https://cdn.tailwindcss.com\](https://cdn.tailwindcss.com)"\>\</script\>  
    \<style\>  
        body { font-family: \-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }  
        .input-group { margin-bottom: 0.75rem; }  
        .card { background: white; border-radius: 12px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); padding: 1rem; margin-bottom: 1rem; }  
        .result-card { border-left: 6px solid; }  
        .safe { border-left-color: \#10B981; }  
        .warning { border-left-color: \#F59E0B; }  
        .unsafe { border-left-color: \#EF4444; }  
    \</style\>  
\</head\>  
\<body class="bg-gray-100 p-3"\>  
    \<div class="max-w-md mx-auto"\>  
        \<h1 class="text-xl font-bold text-gray-800 mb-3"\>VentOptimizer v2.4\</h1\>  
          
        \<\!-- SECTION 1: MODE & STRATEGY \--\>  
        \<div class="card"\>  
            \<h2 class="text-md font-bold text-gray-700 mb-2 border-b pb-1"\>1. Mode & Strategy\</h2\>  
            \<div class="mb-3"\>  
                \<label class="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1"\>Ventilation Mode\</label\>  
                \<div class="flex space-x-2"\>  
                    \<button onclick="setMode('VC')" id="btn\_vc" class="flex-1 py-2 px-4 rounded border bg-blue-600 text-white font-bold text-sm shadow"\>Volume (VC)\</button\>  
                    \<button onclick="setMode('PC')" id="btn\_pc" class="flex-1 py-2 px-4 rounded border bg-white text-gray-600 font-bold text-sm shadow-sm"\>Pressure (PC)\</button\>  
                \</div\>  
            \</div\>  
            \<div class="grid grid-cols-2 gap-3 mb-3"\>  
                \<div class="input-group"\>  
                    \<label class="block text-xs font-semibold text-gray-500"\>R/I Index (0-1)\</label\>  
                    \<input type="number" id="ri\_index" value="0.8" step="0.1" class="w-full rounded border-gray-300 p-2 border text-sm"\>  
                \</div\>  
                \<div class="flex items-center bg-blue-50 p-2 rounded border border-blue-100 mt-4"\>  
                    \<input type="checkbox" id="permissive\_mode" class="h-4 w-4 text-blue-600" checked\>  
                    \<label for="permissive\_mode" class="ml-2 block text-xs text-gray-700"\>\<strong\>Permissive CO2\</strong\> (pH \> 7.20)\</label\>  
                \</div\>  
            \</div\>  
        \</div\>

        \<\!-- SECTION 2: PATIENT DATA \--\>  
        \<div class="card"\>  
            \<h2 class="text-md font-bold text-gray-700 mb-2 border-b pb-1"\>2. Patient & Baseline\</h2\>  
            \<div class="grid grid-cols-2 gap-3 mb-2"\>  
                \<div class="input-group"\>\<label class="block text-xs font-semibold text-gray-500"\>PBW (kg)\</label\>\<input type="number" id="pbw" value="70" class="mt-1 w-full rounded border-gray-300 p-2 border text-sm"\>\</div\>  
                \<div class="input-group"\>\<label class="block text-xs font-semibold text-gray-500"\>Base PaCO2\</label\>\<input type="number" id="base\_paco2" value="70" class="mt-1 w-full rounded border-gray-300 p-2 border text-sm"\>\</div\>  
                \<div class="input-group"\>\<label class="block text-xs font-semibold text-gray-500"\>HCO3\</label\>\<input type="number" id="hco3" value="24" class="mt-1 w-full rounded border-gray-300 p-2 border text-sm"\>\</div\>  
                \<div class="input-group"\>\<label class="block text-xs font-semibold text-gray-500"\>PF Ratio\</label\>\<input type="number" id="pf\_ratio" value="140" class="mt-1 w-full rounded border-gray-300 p-2 border text-sm"\>\</div\>  
            \</div\>  
            \<div class="bg-gray-50 p-2 rounded border border-gray-200"\>  
                \<p class="text-xs font-bold text-gray-500 mb-1 text-center"\>Observed Baseline Settings\</p\>  
                \<div class="grid grid-cols-3 gap-2 text-sm text-center"\>  
                    \<div\>VT (Obs)\<br\>\<input type="number" id="base\_vt" value="430" class="w-full border rounded p-1"\>\</div\>  
                    \<div\>RR\<br\>\<input type="number" id="base\_rr" value="20" class="w-full border rounded p-1"\>\</div\>  
                    \<div\>PEEP\<br\>\<input type="number" id="base\_peep" value="5" class="w-full border rounded p-1"\>\</div\>  
                    \<div\>Pplat/Pinsp\<br\>\<input type="number" id="base\_pplat" value="25" class="w-full border rounded p-1"\>\</div\>  
                    \<div\>Ppeak\<br\>\<input type="number" id="base\_ppeak" value="30" class="w-full border rounded p-1"\>\</div\>  
                \</div\>  
            \</div\>  
        \</div\>

        \<\!-- ACTION \--\>  
        \<button onclick="runOptimizer()" class="w-full bg-blue-600 text-white font-bold py-3 px-4 rounded-lg shadow hover:bg-blue-700 transition duration-200"\>Optimize Settings\</button\>

        \<\!-- RESULTS \--\>  
        \<div id="resultsArea" class="mt-6 hidden"\>  
            \<h2 class="text-md font-bold text-gray-700 mb-2"\>Recommendation\</h2\>  
            \<div id="result\_card" class="card result-card mb-4"\>  
                \<div class="flex justify-between items-end mb-2"\>  
                    \<div\>  
                        \<span id="status\_label" class="text-xs font-bold uppercase tracking-wide"\>Optimal Settings\</span\>  
                        \<div class="text-2xl font-bold text-gray-800" id="rec\_settings"\>--\</div\>  
                    \</div\>  
                    \<div class="text-xl font-bold text-blue-600" id="rec\_peep"\>--\</div\>  
                \</div\>  
                \<div class="grid grid-cols-1 gap-y-2 text-sm mt-3 border-t pt-2"\>  
                    \<div class="flex justify-between items-center bg-gray-50 p-2 rounded"\>  
                        \<span class="text-gray-600"\>Mech Power:\</span\>  
                        \<div class="text-right"\>  
                            \<span id="rec\_mp" class="font-mono font-bold text-lg"\>--\</span\> J/min  
                            \<div id="base\_mp\_comparison" class="text-xs text-gray-400"\>Baseline: \--\</div\>  
                        \</div\>  
                    \</div\>  
                    \<div class="grid grid-cols-2 gap-2"\>  
                         \<div\>Pred pH: \<span id="rec\_ph" class="font-mono font-bold"\>--\</span\>\</div\>  
                         \<div\>Auto-PEEP: \<span id="rec\_tau" class="font-mono"\>--\</span\>\</div\>  
                         \<div\>Result VT: \<span id="rec\_res\_vt" class="font-mono font-bold"\>--\</span\>\</div\>  
                         \<div\>Driving P: \<span id="rec\_dp" class="font-mono text-blue-600 font-bold"\>--\</span\>\</div\>  
                    \</div\>  
                \</div\>  
            \</div\>  
            \<div class="bg-gray-50 border border-gray-200 rounded-lg p-3 text-xs text-gray-600 mb-4"\>  
                \<strong\>Logic:\</strong\> \<span id="logic\_explanation"\>--\</span\>  
            \</div\>  
        \</div\>  
    \</div\>

    \<script\>  
        let CURRENT\_MODE \= 'VC';

        function setMode(mode) {  
            CURRENT\_MODE \= mode;  
            const btnVC \= document.getElementById('btn\_vc');  
            const btnPC \= document.getElementById('btn\_pc');  
            if (mode \=== 'VC') {  
                btnVC.className \= "flex-1 py-2 px-4 rounded border bg-blue-600 text-white font-bold text-sm shadow";  
                btnPC.className \= "flex-1 py-2 px-4 rounded border bg-white text-gray-600 font-bold text-sm shadow-sm";  
            } else {  
                btnPC.className \= "flex-1 py-2 px-4 rounded border bg-blue-600 text-white font-bold text-sm shadow";  
                btnVC.className \= "flex-1 py-2 px-4 rounded border bg-white text-gray-600 font-bold text-sm shadow-sm";  
            }  
        }

        function runOptimizer() {  
            // 1\. Get Inputs  
            const pt \= {  
                pbw: parseFloat(document.getElementById('pbw').value),  
                pf: parseFloat(document.getElementById('pf\_ratio').value),  
                ri: parseFloat(document.getElementById('ri\_index').value),  
                paco2: parseFloat(document.getElementById('base\_paco2').value),  
                hco3: parseFloat(document.getElementById('hco3').value),  
                permissive: document.getElementById('permissive\_mode').checked  
            };  
            const base \= {  
                vt: parseFloat(document.getElementById('base\_vt').value),  
                rr: parseFloat(document.getElementById('base\_rr').value),  
                peep: parseFloat(document.getElementById('base\_peep').value),  
                pplat: parseFloat(document.getElementById('base\_pplat').value),  
                ppeak: parseFloat(document.getElementById('base\_ppeak').value)  
            };  
            const LIMITS \= { min\_ph: pt.permissive ? 7.20 : 7.30, max\_pplat: 30, max\_vt\_kg: 8, min\_vt\_kg: 4 };

            // 2\. Baseline Mechanics  
            const DrivingP\_Base \= base.pplat \- base.peep;  
            const C\_stat\_Base \= DrivingP\_Base \> 0 ? base.vt / DrivingP\_Base : 50;   
            const Resistive\_Gap \= base.ppeak \- base.pplat;  
            const R\_aw \= Resistive\_Gap / ((base.vt/1000) / 1.0);   
            const V\_deadspace \= 2.2 \* pt.pbw;  
            const Base\_Valv \= base.rr \* (base.vt \- V\_deadspace);  
            const base\_MP \= 0.098 \* base.rr \* (base.vt/1000) \* (base.ppeak \- 0.5 \* DrivingP\_Base);

            let recruitability \= pt.ri \> 0.5 ? "High" : "Low";  
            let isHypoxic \= pt.pf \< 150;

            // 3\. Candidates  
            const cand\_RRs \= Array.from({length: 16}, (\_, i) \=\> i \+ 15);  
            const cand\_PEEPs \= \[5, 8, 10, 12, 14, 16\];  
            const cand\_VTs \= \[350, 380, 400, 420, 450, 480\];   
            const cand\_Pinsp \= \[15, 18, 20, 22, 24, 26, 28, 30\]; 

            let bestScore \= 99999, bestSet \= null, bestPred \= null;  
            const primaryLoop \= CURRENT\_MODE \=== 'VC' ? cand\_VTs : cand\_Pinsp;

            // 4\. Optimization Loop  
            for (let val of primaryLoop) {  
                for (let rr of cand\_RRs) {  
                    for (let peep of cand\_PEEPs) {  
                          
                        let test\_VT \= 0, test\_Pinsp \= 0, test\_PEEP \= peep, test\_RR \= rr;

                        // Dynamic Compliance  
                        let C\_stat\_New \= C\_stat\_Base;  
                        let delta\_peep \= peep \- base.peep;  
                        if (delta\_peep \> 0\) {  
                            const recruitment\_factor \= (pt.ri \- 0.5) \* 0.1;  
                            C\_stat\_New \= C\_stat\_Base \* (1 \+ (recruitment\_factor \* delta\_peep));  
                        }

                        // Mode Branching  
                        if (CURRENT\_MODE \=== 'VC') {  
                            test\_VT \= val;  
                            test\_Pinsp \= peep \+ (test\_VT / C\_stat\_New); // Pplat  
                        } else {  
                            test\_Pinsp \= val; // Set Pressure  
                            const drivingP \= test\_Pinsp \- peep;  
                            test\_VT \= drivingP \* C\_stat\_New; // Predicted Volume  
                        }

                        const vt\_L \= test\_VT / 1000;  
                        const pred\_Pplat \= test\_Pinsp;  
                        const pred\_DrivingP \= pred\_Pplat \- peep;  
                        const pred\_Ppeak \= pred\_Pplat \+ Resistive\_Gap;   
                          
                        const mp\_pressure\_term \= CURRENT\_MODE \=== 'VC' ? pred\_Ppeak : pred\_Pplat;  
                        const pred\_MP \= 0.098 \* rr \* vt\_L \* (mp\_pressure\_term \- 0.5 \* (pred\_DrivingP));  
                          
                        const Valv\_new \= rr \* (test\_VT \- V\_deadspace);  
                        const pred\_PaCO2 \= (Base\_Valv \* pt.paco2) / Valv\_new;  
                        const pred\_pH \= 6.1 \+ Math.log10(pt.hco3 / (0.03 \* pred\_PaCO2));  
                          
                        const Tau \= (R\_aw \* (C\_stat\_New/1000));   
                        const Te \= (60 / rr) \- 1.0; 

                        // Constraints  
                        let isSafe \= true;  
                        if (pred\_Pplat \> LIMITS.max\_pplat) isSafe \= false;  
                        if ((test\_VT/pt.pbw) \> LIMITS.max\_vt\_kg) isSafe \= false;  
                        if ((test\_VT/pt.pbw) \< LIMITS.min\_vt\_kg) isSafe \= false;  
                        if (pred\_pH \< LIMITS.min\_ph) isSafe \= false;  
                        if (Te \< 3 \* Tau) isSafe \= false;   
                        if (recruitability \=== "Low" && peep \> base.peep) isSafe \= false;  
                        if (recruitability \=== "High" && isHypoxic && peep \< base.peep) isSafe \= false;

                        if (isSafe) {  
                            let p\_dev \= 0, v\_dev \= 0;  
                            if (CURRENT\_MODE \=== 'VC') v\_dev \= Math.abs(test\_VT \- base.vt)\*0.01;  
                            else p\_dev \= Math.abs(test\_Pinsp \- base.pplat)\*0.5;  
                              
                            const penalty \= v\_dev \+ p\_dev \+ Math.abs(rr \- base.rr)\*0.5 \+ Math.abs(peep \- base.peep)\*1.0;  
                            const score \= pred\_MP \+ penalty;

                            if (score \< bestScore) {  
                                bestScore \= score;  
                                bestSet \= {vt: test\_VT, rr: test\_RR, peep: test\_PEEP, pinsp: test\_Pinsp};  
                                bestPred \= {mp: pred\_MP, ph: pred\_pH, pplat: pred\_Pplat, dp: pred\_DrivingP, tau: Tau};  
                            }  
                        }  
                    }  
                }  
            }

            // 5\. Display  
            const resultsDiv \= document.getElementById('resultsArea');  
            const resultCard \= document.getElementById('result\_card');  
            const statusLabel \= document.getElementById('status\_label');  
            resultsDiv.classList.remove('hidden');

            if (bestSet) {  
                resultCard.className \= bestPred.mp \> 25 ? "card result-card warning mb-4" : "card result-card safe mb-4";  
                statusLabel.className \= bestPred.mp \> 25 ? "text-xs font-bold text-yellow-600 uppercase tracking-wide" : "text-xs font-bold text-green-600 uppercase tracking-wide";  
                statusLabel.innerText \= bestPred.mp \> 25 ? "WARNING: HIGH POWER" : "OPTIMAL SETTINGS";

                if (CURRENT\_MODE \=== 'VC') document.getElementById('rec\_settings').innerText \= \`VT ${Math.round(bestSet.vt)} / RR ${bestSet.rr}\`;  
                else document.getElementById('rec\_settings').innerText \= \`Pinsp ${bestSet.pinsp} / RR ${bestSet.rr}\`;  
                  
                document.getElementById('rec\_peep').innerText \= \`PEEP ${bestSet.peep}\`;  
                document.getElementById('rec\_mp').innerText \= bestPred.mp.toFixed(2);  
                  
                const diff \= bestPred.mp \- base\_MP;  
                const sign \= diff \> 0 ? "▲" : "▼";  
                const colorClass \= diff \> 0 ? "text-red-500" : "text-green-500";  
                document.getElementById('base\_mp\_comparison').innerHTML \= \`Baseline: ${base\_MP.toFixed(2)} (\<span class="${colorClass}"\>${sign} ${Math.abs(diff).toFixed(2)}\</span\>)\`;

                document.getElementById('rec\_ph').innerText \= bestPred.ph.toFixed(2);  
                document.getElementById('rec\_res\_vt').innerText \= Math.round(bestSet.vt) \+ " mL";  
                document.getElementById('rec\_dp').innerText \= bestPred.dp.toFixed(1);  
                document.getElementById('rec\_tau').innerText \= "Safe";  
                  
                let logicText \= \`Mode: ${CURRENT\_MODE}. Target pH \> ${LIMITS.min\_ph.toFixed(2)}. \`;  
                if (CURRENT\_MODE \=== 'PC') logicText \+= "Optimized Pinsp to control Volume. ";  
                logicText \+= recruitability \=== "High" ? "Recruitable Lung Logic Applied." : "Non-Recruitable Lung Logic Applied.";  
                document.getElementById('logic\_explanation').innerText \= logicText;

            } else {  
                resultCard.className \= "card result-card unsafe mb-4";  
                statusLabel.innerText \= "NO SOLUTION FOUND";  
                document.getElementById('rec\_settings').innerText \= "Unsafe";  
                document.getElementById('rec\_peep').innerText \= "--";  
                document.getElementById('logic\_explanation').innerText \= \`Could not meet safety limits (pH/Volutrauma/Pplat).\`;  
            }  
        }  
    \</script\>  
\</body\>  
\</html\>

## **5\. Source Code 2: Research Engine (MATLAB)**

These scripts map functionally to the web app for batch validation and testing.

### **5.1 Run\_Optimizer\_v2.m**

% VENTILATION OPTIMIZER (Research Engine)  
clear; clc;

% Inputs & Strategy  
Pt.PBW \= 70; Pt.Base\_PaCO2 \= 70; Pt.HCO3 \= 24; Pt.PF\_Ratio \= 140; Pt.RI\_Index \= 0.8;  
Permissive\_Mode \= true;   
Mode \= 'VC'; % Toggle to 'PC' for pressure control mode logic

Base.VT \= 430; Base.RR \= 20; Base.PEEP \= 5; Base.Pplat \= 25; Base.Ppeak \= 30;

% Baseline Mechanics  
Base.DrivingP \= Base.Pplat \- Base.PEEP;  
Mech.C\_stat\_Base \= Base.VT / Base.DrivingP;   
Mech.Resistive\_Gap \= Base.Ppeak \- Base.Pplat;  
Mech.R\_aw \= Mech.Resistive\_Gap / ((Base.VT/1000) / 1.0);  
Mech.Base\_Valv \= Base.RR \* (Base.VT \- (2.2 \* Pt.PBW));  
Base\_MP \= 0.098 \* Base.RR \* (Base.VT/1000) \* (Base.Ppeak \- 0.5 \* Base.DrivingP);

% Limits  
Limits.Max\_Pplat \= 30; Limits.Min\_VT\_kg \= 4; Limits.Max\_VT\_kg \= 8;  
Limits.Min\_pH \= Permissive\_Mode ? 7.20 : 7.30; 

% Grid Setup  
Cand\_RRs \= 15:1:30; Cand\_PEEPs \= 5:1:16;           
if strcmp(Mode, 'VC')  
    Cand\_Primary \= 350:20:480; % VTs  
else  
    Cand\_Primary \= 15:2:30;    % Pinsp  
end

Best\_Score \= Inf; Best\_Set \= \[\]; Best\_Pred \= \[\];

for val \= Cand\_Primary  
    for r \= Cand\_RRs  
        for p \= Cand\_PEEPs  
            % Dynamic Recruitment Compliance  
            C\_stat\_New \= Mech.C\_stat\_Base;  
            if (p \- Base.PEEP) \> 0  
                C\_stat\_New \= Mech.C\_stat\_Base \* (1 \+ ((Pt.RI\_Index \- 0.5) \* 0.1 \* (p \- Base.PEEP)));  
            end  
              
            % Mode Branching  
            if strcmp(Mode, 'VC')  
                Set.VT \= val;  
                Set.Pinsp \= p \+ (Set.VT / C\_stat\_New);  
            else  
                Set.Pinsp \= val;  
                Set.VT \= (Set.Pinsp \- p) \* C\_stat\_New;  
            end  
            Set.RR \= r; Set.PEEP \= p;

            % Predict & Check Constraints  
            Mech\_Temp \= Mech; Mech\_Temp.C\_stat \= C\_stat\_New;  
            Pred \= predict\_physiology(Set, Pt, Mech\_Temp, Mode);  
            \[IsSafe, Reason\] \= check\_constraints(Pred, Set, Pt, Limits, Pt.RI\_Index, Base.PEEP);  
              
            if IsSafe  
                Score \= Pred.MP \+ abs(Set.RR \- Base.RR)\*0.5; % Simplified penalty  
                if Score \< Best\_Score  
                    Best\_Score \= Score; Best\_Set \= Set; Best\_Pred \= Pred;  
                end  
            end  
        end  
    end  
end

% Report  
if isempty(Best\_Set)  
    disp('No safe settings found.');  
else  
    fprintf('Mode: %s | Best Score MP: %.2f J/min\\n', Mode, Best\_Pred.MP);  
    fprintf('VT: %.1f | RR: %d | PEEP: %d\\n', Best\_Set.VT, Best\_Set.RR, Best\_Set.PEEP);  
end

### **5.2 predict\_physiology.m**

function \[Pred\] \= predict\_physiology(Set, Pt, Mech, Mode)  
    Pred.Tau \= Mech.R\_aw \* (Mech.C\_stat / 1000);   
    Pred.Te \= (60 / Set.RR) \- 1.0;  
      
    Pred.Pplat \= Set.Pinsp; % In PC, Pinsp is roughly Pplat. In VC, we calculated it before calling.  
    Pred.Ppeak \= Pred.Pplat \+ Mech.Resistive\_Gap;  
    DrivingP \= Pred.Pplat \- Set.PEEP;  
      
    if strcmp(Mode, 'VC')  
        Pred.MP \= 0.098 \* Set.RR \* (Set.VT / 1000\) \* (Pred.Ppeak \- 0.5 \* DrivingP);  
    else  
        Pred.MP \= 0.098 \* Set.RR \* (Set.VT / 1000\) \* (Pred.Pplat \- 0.5 \* DrivingP);   
    end  
      
    Valv\_new \= Set.RR \* (Set.VT \- (2.2 \* Pt.PBW));  
    Pred.PaCO2 \= (Mech.Base\_Valv \* Pt.Base\_PaCO2) / Valv\_new;  
    Pred.pH \= 6.1 \+ log10( Pt.HCO3 / (0.03 \* Pred.PaCO2) );  
end

### **5.3 check\_constraints.m**

function \[IsSafe, Reason\] \= check\_constraints(Pred, Set, Pt, Limits, RI\_Index, Base\_PEEP)  
    IsSafe \= true; Reason \= 'Safe';  
    if Pred.Pplat \> Limits.Max\_Pplat; IsSafe=false; return; end  
    VT\_kg \= Set.VT / Pt.PBW;  
    if VT\_kg \> Limits.Max\_VT\_kg || VT\_kg \< Limits.Min\_VT\_kg; IsSafe=false; return; end  
    if Pred.Te \< (3 \* Pred.Tau); IsSafe=false; return; end   
    if Pred.pH \< Limits.Min\_pH; IsSafe=false; return; end   
    if RI\_Index \< 0.5 && Set.PEEP \> Base\_PEEP; IsSafe \= false; return; end  
end  


[image1]: <data:image/png;base64,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>

[image2]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACkAAAAaCAYAAAAqjnX1AAACu0lEQVR4Xu2WO2hUQRSG78UHior4WNfs697dFRZXsFksFAURCxtF1EJQSCGoaJU0GokSC7EKPgoFEV+NCEosTII2BgUt7MRCtBBBFC1FLBSi3++dNfcedk0w2aTZH35m5vxnZ86cmXtmPa+NNiKkUqmFYRhuLhQKe4IgWI1pluzpdHpBNpvNGffpBUFVCeo5/EaQd2i74S36j9DW0B+m3Wp/Ny2o1WpzCKAX/iCg47lcbn5cz+fzm9C+wg8zkkkFSHYuE8BPuNvqAoHPQxsU1bd6y8Gih1n8F20PQ9/qdaDfxO+EtbccHOsqFv4I32YymbzV48Dn6ozcR7LTpyzCM1azKJVKi3U1rL2lUJkhuBE4OiMZmggIrgO+h58IsmT1/4SvWmqNzVCtVuf+83RiQYodVo/DfVwbrN0Cn/VwUKdktQaYje9tErTdCn+BuASnF+MFSV1chn6tXC6vsJpFEBX/i9beCMViMR1ED4detObAoR+OkqltVnPw3cKJ+qkjxXYSDsF9sMgcF2jfBdE979ZRylevGLyOfhr7FirKUtoDcAB+lkbAa+PzJ4AY4PSGCZ7AlXFNrw7aKexdXrJ++tjPwo38vsJCw8o2JWw5/cdBLDO8VDsY39Px019H/3X9/jPvoWCCWZdziPMz+J0JbjDsdFl5qp17psCHY6/PK22AxTOyK2j4sFKpLNJYJctt/s8pqYJoQ+7D0n28C3fFph4XvoIFO0UWLnvun08jSHcb+QL7ZQtNZgiqhu1l/a1nfCxw9bhR1qcMLosDWlBjZQJbnxfLjF4ubJ0KEt7XUevqoA254z+irNazTrsfWzG50uSgjPcw6VEmP0h7JYzusu7peWUV9uqo3WMhvQvtHP0H8BLjvYXob9+I5gqbf7STgwJoUAt9dx8Td9jZdHUShV6nIo55ttFGG1OC37csqYie6fMPAAAAAElFTkSuQmCC>

[image3]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACEAAAAaCAYAAAA5WTUBAAAB5ElEQVR4Xu1UPUvDUBRtQUFRdJAabJK+Js0iuvUXiA46CZ0EdRLEwVXcBAcnwcFF0MFRBBFBCg4OHcW5IDipCKKizjqo5zYJ3t68xLoIhRw4tHnn3vvuO+8jk0nRJsgWCoVFcFwK/wbbtkeVUm9gvVQqDUpdB8QugK/gF+MTG3sEVyzL6pa5OmQRvAV+UnKxWFySAXEwDKMHOefgA1x0mZRFnWmMv2N8B98dTIsCQSMIPgVnqREkX5qmOSDjdECchZx7aoQa4hrGhsBb8AUc5ppEwwU0Mke24feM3KBvGagD4iYCBzc0mksOaVxqBib2EHQcrhwuTAZFL1zX7ZfxEii+Sk2DU1JDrZlAO8gkbAft2zpfdS6X60VSjZKpCIuNAHoX4qq6lTqOozB2Da1O/7nWBAQ44JHcf4xVWnEDLpqIuQGfMeE+fneJaO5Q+Tdj0/O8PpnXBCSu6W4CTUwNBI1UpB6CnYc95R/CBrFyo1wud8r4CJTvQjXuTWD7WaMtkjqBnYfYRhMRFFiW4yG4G3RYpc7Ow6/XT4t8Pm+jiROyTWocdGBppXRt5avH3odYpxJBDoAfKH6XROU/wWR3xA12lbf5eEug1SPxKij+F54Gj9m8+mkuJD1IY3KuFClSpGhrfANfKqyX9Qxv3QAAAABJRU5ErkJggg==>

[image4]: <data:image/png;base64,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>

[image5]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAsAAAAbCAYAAACqenW9AAAAqElEQVR4XmNgGAV0BcbGxqyKiori8vLykuhYVFSUB64QKGAJxK+B+D8OvFVBQYGDQUZGRgXIOQDkeABpSSAdAKQng9gwDFYIAkBGhKysrDKSLa1AsXS4tbiAnJycIBAfBGIbdDkMQKpiY6ATLklLS8ugy2EAoOJyoJsPq6ur86LLoQBgqHACFe8AmrwQXQ4DKCkpqQFNfU1USAABM9CtwiAaXWIU0BcAANcxJna8SS8PAAAAAElFTkSuQmCC>

[image6]: <data:image/png;base64,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>

[image7]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABQAAAAaCAYAAAC3g3x9AAABWUlEQVR4Xu2TO0vEQBSFE1bBQhGVaJF3AsbOItgJgmwh21tZ+8LKQvwNtqLdioqVIvhDBFsrQSwtLMStBPW7kJHZkX0kiFjsgUNmzj33zs1NxrIG+BWEYbgMH4IgeOqTdbOGDptiR1EUXcJI9iKiNeEH0krhq7FeQnv0fX/hO9tEHMczGK/SNJ1WGh1MkHgryZ7nuUp3HGcU7cJ1XU9pPyDtU3BX1zhknsRXeM12SOnFQYdZlo1p9nZgWk2SZFbXSFqDn8T2dZ3OptA2rGIsfaOY3zvJi2asNDrNrzIomFOsZc6vMjrNrypsCp3+9fxqxBt4z4S9/smu88vzfJjYMdxja8uNIWe9zST/IIY7+CKz0/gG7+UQ5WVdR3vmImzBbdbNrh32gnwoitxIp2asEuhqE56rPW83zn5O95SCFKDDE3llnjs8D/h4k6avLGy50xQbMQMD/FN8AROVXk2qiLrlAAAAAElFTkSuQmCC>

[image8]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEQAAAAaCAYAAAAOl/o1AAAC5ElEQVR4Xu2WTYjTUBDHU1q/P1FraWubfknZHkSoIgiCiqAHUREEQU/ufUVEBFm8iYfqwUUUP0A8yHoV9KCIi3oRFFFY8KyIoLJ6cUU8uP7GJpKdJiZNl6XC+8GftO/NTN6bzJvEsgwGg6E/SZRKpU22bY+gS8Vi8UAmk1mkjfoSFrwNPWMDB5vN5hw9H4MUsS4Q80w+n18Da/n/hP/j5XLZ1sZ9CYtewIKPoFdosJenif8AmiAJD9Lp9GJn7BCakorR9n2NVIhUCgt/gYZrtdpSbRMGVVDH9yN6TYWslDF+73cScl3bK+SoleSqxv8iMXt5YHFJsvjt6ClquRuLCnta7lYHJIhxEf2SxEwz7CSFzSn8j1k+SbHb1Xcv6tEjznzss36SOW0fBbc5jjmbymqDEMR/J35f0LkoPUpssG2hE5YnKV0mIyGNHPufdrsy/RT/+HJ05nGD0wR5T7+p6Xk/sN+B3uHziaRcyeVyq7RNEDopdnfJsAqFwhbsH3H/Jtcs1yGJJb9FxMlEeTgdeJstQY/GPLtJfM8S46skSU8G4UnKtW6S0Wg05sqaPcdcjuFoN/fuQDYuCSDQy5l4HfPENhLrOxqvVqur9XwQ+G3A5wMatnx6ShTYRwX/53LVc6HIW0Vubre/S/YylNQ2YfAk1+E/Ild3zG6X6ls0KWXstQ+C+6/H9r58xzjHdVpPiQpJ3YP/43q9vkTPBeIsWJrmGNpsxUiECxu5SYwpubpjzlmeRBNowGvvh5sM95hIhcZMijTXG/jdkt960hccdqM7zhON5vQPiHWSBXxmU7s8Y4clSVwv8zflMe9AkoHtXd0z4iRFmif2b2RNem7WqFQqy1jEKHqIBtFx9I1F3ZY5be+FN9FCbFs6GR6kQcsbQ6o4FJK7FdsfxV4a6gwh3x/CPhEbLWiD2UCqih60wopYUX8QJ6e0Or7mtJw3ROz+8l/gnNmrEXVeEqNjGAwGg8FgCOM31p/A163cbqoAAAAASUVORK5CYII=>

[image9]: <data:image/png;base64,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>

[image10]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFcAAAAaCAYAAADCDsDeAAAEo0lEQVR4Xu2YTWhdRRTH80gVxY/6lT6bNG9eXiKhUYQarSh10VawWVSlKCgVuiil4kIlLgrSriRUUKFGUazFKlLqR6gL+6UV2tqCAVeVrgTxY2HRogWxggiJv3/mTDud3Pde8vJMLL1/+HNnzjkzd+65Z86Ze1tacuTIkSPHnMA5txyeguMRf4e/WvvPUqm0raen59p07EWMQrlcvptnG4Zv8HyPFovFq1IjPTO6Z7DZDrfAhanNlMDAHfAfJluWyO+Qo1nM521tbVfHuosU83iWV3mmoY6OjkXgFvpf0j/Z1dXlgpHa4AT+2ID+CtoDtL9FvjSerC56e3uvYfAx+B2Di7FODkV+BI4x+f2xbjagiOrv778slTcKnmMx/C0OFvprnd+lw2Y2z/lgG1E7GjuEDw7yQq4MsroIN0wnE5jseuRfu4yong1w33vhMW3PrK07XRA8vcz3CzxB5N4oGe015twd6nOvCu1TXDfFY83uLPL+WF4TnZ2dD9rkg6kO2T3wbzhaqVTmp/pZQiv3X+H87nopOKVRELXXRSmuwJyvwzE5TwLtUPVT59JfbX5aG8trwvnEPiky5UzkX8DTvIA7Y90cIRSiw+aQxgrMeWi+B5wv4C+H9BOcWM25qbwqopyq6NzlfGXczk3f4/ozE+1U4k/HzTEKbO/bWd8BOKKtnhrUg6IT/uR8sX6rvb39pki3KcuJ03auO59vD1mFXBioKpnap7BiuBv+QXTfleozUGhG7gywHDoC9zTiZNCKs7Yy/owcLgHtwSwnTtu5Ub59PtVNFc6/oMPx268G53P4vmYe65hPUbEHfqJ8murrQUHB2L/gye7u7gXVnFhNXhXO59ux8NYagfNHmUknjSw4HxXhyDMjWNR+LE41ai2dDOsaZM7v1B+dnQTgMudrUKZznRW+mojOtz9wdutI9RGU+Ncx+bssainXF7VAZDdLae2NwVjnQPXhR1qIFlz20OH9e+dz/GBfX9/l5+4wdYR8uxe+DbtSg1qwWjKua5BpfcjOOp8eF8sX8omeKxm7MdjE8kywHW7D8AzcV66RX7n5rdgMOCt4qqrOO20nC7mB61G9bdlagdzLfKvo6pijMUPSKW04X+nrL24ymnIcUzQy/rStL8iecH67v9nid5/W/YKLjp96ZguW3WaTDZx6n/PbYDyijiPrU1tBeYgx3egP6S1L5nwqOGJv/Vy+ZQGP0d9v0avPxk/hgHR6AfAz7Zh4/jpoZZ6HmGMUbp7pPw47XqoA64i5Hj7n/P+TD+JzvNnt594fav3wHXj8Pzk5mROPmxMLilrn8/UF+da23URxtO2lr6uK6bStppVvGfNkqUlfZxGU5oSHRZ6pMzUw6CShHPyIBVVratAUmBN30SxoMbS/gkvkLDkNrpPj5VwWslpjaK9Cf4D+SlEvAa7ReNknt7hkMRGpOOQbrk87/6GxQgqum+FryDfIruy/eN7n+qzskB+EWylCRa7bkL2iMXP4Kf3/Qsn/vJnIt5Yv4+1RMFkhCJT8wzbWiSD6qzXJ9pJH2X/Pj1JM2lJdjhlA1RHnPu58ZX2qpdYxJEeOHDlypPgXTGVjATp2oWMAAAAASUVORK5CYII=>

[image11]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACoAAAAaCAYAAADBuc72AAACpElEQVR4Xu2V34uMURjHd7Lk96+MsTPvzJlf7bRDkeFCrSJbolYut8iqdaOQ9gZbyh9AWK42hQspyc0yYvdCjYstbpTcKXtDEW72Rgqfb+95czom0uqdVfOtb+c8v877nOc857wdHW208R/BGLMTvoPfHX6C7+18JpfLXSqXy8v92JaAhK7BryTV6+k3K+l8Pv84mUwudW2xo1KpLCOZBnxdKBRSrk3JoX8Cv7GJPtcWO0iiB36EdxE7XRvJrUL/rFm1Y0c2m91n+3HYt6HbBr/AqWKxuMK3xwqSGG1WMSWGfhJ+YDNbXFvscHpQVbsFx0Quz03GtyR/PZPJBH5c7DA/+3OCi8RguiKS7ELXVxVGd7QlLeD054hv88FGNuJ3tSXPlAn7s/VPz+/gvJ9vgiDI+HYHCY58P351xk1SsLF+5ncY16M/Ah8iH5ZvFIS8Dv0FeB+/XTauD/meCV+TEeQbtFJ3FNMUHPsGnD/DB34/ujBhH+/Rwvid06aYD9kPPUJebcK+1qXsUgy6RczHsBeJ2aFN8RsOkA8qDk6q18lhK/Pxpu2EcTvGafPr/33I9xVKpdJaFs1hr+sJU2JWHlePywd9DflpOp1eI1kj8kvYIMlB/TgUp00qaSeuF59Xxm5w1jDhUU1EN95WtaGKWfsxOOrG6O3V0aKfiYpg46Zgj2Tsp8wfTvSvoCTsonvVMrYSdR2ZfYvrOin0J3h3u5FfMO9XLEmcgQOaK07tovuhOM2j6v4TmPBSXGHh44gJ5sPqV9lsorfhWXS7bX+ex/cQ8knGi6lUaol87Wan0Z+Gl5kf0HrOp2aNhKqgUUK1Wl1Qq9XmO/Z59OViR1YlV3pH2hn1pxL34ucO2EiWCj5X6/i2OQNb3QEdtY696XPURhshfgDURLrBHjjOGgAAAABJRU5ErkJggg==>

[image12]: <data:image/png;base64,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>

[image13]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEUAAAAaCAYAAADhVZELAAADZElEQVR4Xu2WPWhTURiGE1JF8W/QGpsmuWlaDc0mQQqKCFJBh6pUB1EREcRFrFSoKEUU6aBDh1IQpKCl0IIWxE1FVHApVETEUgcdFNFBdKuDUPV5zQ09OUmTG70Wh/vCx73n/d7z953v/IRCAQIECOAjYrHYGsdxnmI/DfueTCbbC5psNrsYbszU4O+Rr7m5eS3lR5TfezG0/XO9Lxyampoy9H0Vu844Dkej0WW2pgQIOzTZVCo1bPtcRPCPYudzudyiAol+J9w0320FnvIuN3iDFMPiEolETMFT/ULdhQJ97mN8t/i2NjY2xpnrKf4nCZRja4uAMIdwBhunWGf7abQN30g8Hl9q0GG4furuMDgNok9BIRC7TR7dWfhOk7MQzmQyK/S1HX8KJh6l33sKhkFr3IPM6aLBlYKKaYSfsCf19fXLTZ8Cgf8mvo0mr60Hf83UKy3RPVRbatPUM4hzBGqTyVmoQ3Oauo+x7ZQjtqBWuIv9mjmst3gt0JDJlUARRfQWe4c1mD7tQQZ7KWStIHwWfq/FzRtcfMd1BplcOSiwaLto4zntHzC3a60wxvNGW1xcOp1exf8DO5NLoAloItgXrLXAUzlF+Y6XyQjO3HnSZ/tqhTKUdo5hL/S1tq5XhAlMjzsmXRA3sLv8n5HPFtuoQziOfTNSPExMrlSNqAEFQ53XUqcalCnKGOwlbfe2tLSstDVVoEvi97hc+5zMn4NVg6IJDbnR7FCZiW2lPOg1fY1sKzlPfEKEwOyh/Unav+AxODpUT2q78N3sZokCM8v/EVtcAvfwUYVu7Tu+Y6Rsi62bD5XOEx8R0SrTx5ST3wIV4WpfcSkkXEpZc9DJ37TTOkuLKthA1OkGRanWTXRP2JpK0JYp1Ld9PqCQJRNODVvIyWf/gM2n8u+rrwQtZ/uKgKAd4Q9FEBupdbXdYP6T80TBYHxdnl6iBqg7XG6R9G6Bf+YYl0pZKGpOPq1maKzN9leC3+eJX9eym71TukUNWhfIUfjRUJmHahEQNTj5d8rlkIeTmYaXJPOPuo/KEMNmsQ+Ohz1vQ9uCer3YhLZL6O8fcDqDdCXrqaF2D2G34e7T/jpbXAKtBuIttaaoX9ATnwEPOD69Zk2wXVYztw5sP5fIhpCHRQ8QIECAAAECBPjf8AuIufaK31LDmwAAAABJRU5ErkJggg==>

[image14]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAACcAAAAaCAYAAAA0R0VGAAACnUlEQVR4Xu2WO2hUQRSG9+KDiC8U19XsY/YFS1YbXR8IWvgATaFFKsUiRZBACpEtxVa0EaJ2IkSRIIidxleERCIYsLMXtVFQVBAbEdTv3zvXTCarLG68afaHn5k558zMPzNn5t5EooMOFhDGmL3wHfzp8BN8b+tfc7nccLlcXuX3jQ2IuAq/I2S3Z98qofl8/lEymVzh+mJBpVJZiYAp+LJQKKRcnwRhn4Q/EH7A9cUCJu6BH+FtmotdH4LWYH/ebFdjQTabPWLzq+77sO2C3+B0sVhc7fv/O5j4UrOdkRjsj+EHFrDN9cUCJ6e0O6PwisgFuE75FsEj6XQ64/eLBWYm38a5DBRmY0QEdvnxPuxlugm/sLvbfX8TBKlUarlvbAon3077vlZhFzjR3d29zvf5MGEOj7X0LJkw39p6Juh/3DS56c1AXF1z+vY5cN6315lMJu37HQQccT8LuMbR76A8rwmwbZDT1gejYMZapja8ha+P+Fo+xEXar0yY4/Vqtbr09ww+ONLNBH2GY3/LLwbfREyvsRemVqstsZOOIGQt5ZPoptsLdpfxDtEMbJ+z8unYqU/AnlkTuEDUHgLemLnf0wE/ViiVSuvpU8I/rl2QzYRHOam2JozyDVFHad+zu9dF/Q7slU8LgA91Yu74bcOKeGpFBNo1E+brrHzLh09Q43IpVahPEVu0vkH1mRl1nmBFjFINEJil/gxu0WQ2v/olXOIQc1h9dLT479PeL2oRsE/9Fe9N8c9o7BQDvqA8acKHep8clGfgZewnFEfMQdo3KE8pDvsDeE4/FJTD2C6oz7x9CnPhx7+RbzZfFjnuwNqCyKALEz20upFq/ym2bbALOxE3zQ9n0vctKPRdRdwxxA3AoUQLD20HHXj4BbPAt8zNXAh6AAAAAElFTkSuQmCC>

[image15]: <data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAEMAAAAaCAYAAADsS+FMAAAEM0lEQVR4Xu2XX2hWZRzHz8sMDLNctkbv9r7P/uFYCIKzINCiqJGQEZvUyMgLwS4KFI3CXXTnnULNC0OMFbEKKiLClOxCVGq2i1ASQRQ2LyYpOhIVIub8fD3P2ft7nx239527CDxf+HLO8/vzPL/nz+93nhNFGTJk+L+joaFhaaFQ6GpqanoNNiHKJfK2tra6cusy5PDLF4vFdaHvvMA59zy8CCcNr8JL/v06g39MkA+HvlUiR18vwDO+78/gdvg9HGxubl7B3I7y3hE6ghpieB2exeYL2IvdJvgn/M0vyvyBTvfD/xhwdSBfqeAZ75e6urqHrK5S1NfXL6LfAfq5Dt9EVGP16N5CPgGPtbe3L7a6lpaWR9B/w/h/hJOWDp9f4RlOVaPVzRkKQIHA8+xQvdVpAZAfgbcI6kWrqwQ+4INwnL6fDvVCPp9/DP1p2G/lia9OBL7O6hIoJsUG3wt1cwIddcAr8DuaC6yOwWqRD7uUU1MBckoxBcumvhEqE5gF7zbixHeC50tGXgZ0LS5O8wOMsTDUVw2K0qsurg/bQh2yZ+C/cEg7ZXWdnZ0P4LuKXXtW71YnoFvjfY/MlGJ+Mb51pl4kvkz2UGNj44PW3sIsxoxjVAw66ncpO29y8rImbXXswnPwlIuL4LvwdzgO13qTBbx/7eJF3mB9U6BTUBuVaknFvopZsbv5WAxzRLWDg3CfqKrNc4zBBsLipNxH97c9+rR3whvYd6rNbjbQHnFx+qV9Ie6KanyJ4R0XL9pgdK+fWQ3mBz2sIgWeSJiWg2bxytLGxV+j0yqGamtRaN+Aw37XK4bxneovDYoPmwNwkvdeyZRS+G9Gtk/PmVJsGky96At1aSiWqvdOI7tTZHWKIr87ZkKzHV+lyEcE3ZYIKvU1dn+1trY+HsXp1ccmLfOL8jntr9LqWSpcXC9uaZKhLg3YfRja68KE7JqOrLGrqLBpEbD91O6gK53Wu/pqglp8bCa0oZK5+ESPOv8hKMb1ZEzxlXunwNwvRpSnoT4NfjGu2QFob4A3Ceop1RHee/wR/gGOI19u+0igCaHfHd4/fOEeghe1qFaXQGO4uOh/EJVqRU59mVTVKR5zs9SdO1CQCtZV8Y3G7mXsr+qIqq06w/tZZKMEUeC5JxncF1r1/6VuobYfXe9dXKzt3WIKPn0nGG9HVF4YlVZvo/uH55YouM0aKGX2Y7NX76FyCv4bruM0aaj/kU2hbQi/m7vgcf/F+Qn2MOgFnj8j2xqZ4HVakJ9z8ZX+E7ixGOfyYZ5Pmq5DaNKvYDfO80cVSMXH+wmNPYuvTk437K+qgM4VBLdEf5mRn7hOlm0HqCGwDiawHq7Tn2eUbjcNycVOvjy7/BgzgrHWwu3yVWFlQR4Nbe4L+NTs04K7uKC+H96T7gvo1DD5k648/af9CWfIkCFDhgzzi9tEO02tPDp3swAAAABJRU5ErkJggg==>