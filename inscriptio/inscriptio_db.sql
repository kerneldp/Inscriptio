-- phpMyAdmin SQL Dump
-- version 5.2.3
-- https://www.phpmyadmin.net/
--
-- Host: localhost:8889
-- Generation Time: May 10, 2026 at 05:20 PM
-- Server version: 8.0.44
-- PHP Version: 8.3.30

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `inscriptio_db`
--

-- --------------------------------------------------------

--
-- Table structure for table `reports`
--

CREATE TABLE `reports` (
  `id` int NOT NULL,
  `student_id` int NOT NULL,
  `uploaded_by` int NOT NULL,
  `original_img` varchar(500) DEFAULT NULL,
  `shap_img` varchar(500) DEFAULT NULL,
  `gradcam_img` varchar(500) DEFAULT NULL,
  `severe_anomaly_img` varchar(500) DEFAULT NULL,
  `patch_scores` text,
  `findings` text,
  `softmax_score` float DEFAULT NULL,
  `label` varchar(50) DEFAULT NULL,
  `validated_by` int DEFAULT NULL,
  `verdict` varchar(50) DEFAULT NULL,
  `notes` text,
  `session_date` varchar(20) DEFAULT NULL,
  `is_deleted` tinyint(1) DEFAULT '0',
  `delete_reason` text,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `reports`
--

INSERT INTO `reports` (`id`, `student_id`, `uploaded_by`, `original_img`, `shap_img`, `gradcam_img`, `severe_anomaly_img`, `patch_scores`, `findings`, `softmax_score`, `label`, `validated_by`, `verdict`, `notes`, `session_date`, `is_deleted`, `delete_reason`, `created_at`) VALUES
(1, 1, 1, 'uploads/stu1_20260510163911_original.png', 'uploads/stu1_20260510163911_shap.png', 'uploads/stu1_20260510163911_gradcam.png', 'uploads/stu1_20260510163911_severe.png', '[{\"patch_num\": 1, \"pd_prob\": 51.6, \"label\": \"Dysgraphic (PD)\", \"confidence\": 51.6}, {\"patch_num\": 2, \"pd_prob\": 10.6, \"label\": \"Normal (LPD)\", \"confidence\": 89.4}, {\"patch_num\": 3, \"pd_prob\": 8.0, \"label\": \"Normal (LPD)\", \"confidence\": 92.0}]', 'No significant dysgraphic patterns were detected in this sample. The handwriting exhibits characteristics consistent with typical graphomotor development. SHAP attribution values remain below decision-relevant thresholds across all spatial zones, indicating that neither letter formation nor inter-character spacing shows statistically anomalous patterns relative to the model\'s training distribution (APA, 2013).', 0.7656, 'Low Potential', NULL, NULL, NULL, '2026-05-10', 0, NULL, '2026-05-10 16:39:12'),
(2, 2, 1, 'uploads/stu2_20260510165016_original.png', 'uploads/stu2_20260510165016_shap.png', 'uploads/stu2_20260510165016_gradcam.png', 'uploads/stu2_20260510165016_severe.png', '[{\"patch_num\": 1, \"pd_prob\": 24.4, \"label\": \"Normal (LPD)\", \"confidence\": 75.6}, {\"patch_num\": 2, \"pd_prob\": 49.0, \"label\": \"Normal (LPD)\", \"confidence\": 51.0}, {\"patch_num\": 3, \"pd_prob\": 85.6, \"label\": \"Dysgraphic (PD)\", \"confidence\": 85.6}, {\"patch_num\": 4, \"pd_prob\": 57.0, \"label\": \"Dysgraphic (PD)\", \"confidence\": 57.0}]', 'The predictive anomalies are concentrated within the character strokes themselves, suggesting disruptions in graphomotor execution. Kushki et al. (2011) identify that children with dysgraphia exhibit significantly increased pen pressure variability and irregular stroke formation, reflecting underlying motor planning deficits. Overvelde and Hulstijn (2011) further demonstrate that letter formation errors - particularly in stroke direction and sequencing - are reliable markers of Dysfluent Dysgraphia. These motor-level irregularities, concentrated in the ink stroke zones, are consistent with impaired kinesthetic feedback during handwriting production, as described under Specific Learning Disorder criteria (APA, 2013). Döhla and Heim (2016) note that such graphomotor deficits frequently co-occur with reading difficulties, warranting comprehensive assessment beyond handwriting alone.', 0.5399, 'Potential', NULL, NULL, NULL, '2026-05-10', 0, NULL, '2026-05-10 16:50:17'),
(3, 3, 1, 'uploads/stu3_20260510170311_original.png', 'uploads/stu3_20260510170311_shap.png', 'uploads/stu3_20260510170311_gradcam.png', 'uploads/stu3_20260510170311_severe.png', '[{\"patch_num\": 1, \"pd_prob\": 16.8, \"label\": \"Normal (LPD)\", \"confidence\": 83.2}, {\"patch_num\": 2, \"pd_prob\": 16.9, \"label\": \"Normal (LPD)\", \"confidence\": 83.1}, {\"patch_num\": 3, \"pd_prob\": 49.7, \"label\": \"Normal (LPD)\", \"confidence\": 50.3}]', 'No significant dysgraphic patterns were detected in this sample. The handwriting exhibits characteristics consistent with typical graphomotor development. SHAP attribution values remain below decision-relevant thresholds across all spatial zones, indicating that neither letter formation nor inter-character spacing shows statistically anomalous patterns relative to the model\'s training distribution (APA, 2013).', 0.7219, 'Low Potential', NULL, NULL, NULL, '2026-05-10', 1, 'Discarded by user', '2026-05-10 17:03:12'),
(4, 3, 1, 'uploads/stu3_20260510171802_original.png', 'uploads/stu3_20260510171802_shap.png', 'uploads/stu3_20260510171802_gradcam.png', 'uploads/stu3_20260510171802_severe.png', '[{\"patch_num\": 1, \"pd_prob\": 99.9, \"label\": \"Dysgraphic (PD)\", \"confidence\": 99.9}, {\"patch_num\": 2, \"pd_prob\": 99.9, \"label\": \"Dysgraphic (PD)\", \"confidence\": 99.9}, {\"patch_num\": 3, \"pd_prob\": 99.9, \"label\": \"Dysgraphic (PD)\", \"confidence\": 99.9}]', 'The predictive anomalies are heavily localized in the whitespace between characters. Deuel (1995) defines Spatial Dysgraphia as producing illegible writing - whether spontaneous or copied - due to a fundamental deficit in spatial perception, which manifests directly as abnormal letter spacing and erratic kerning. Chung et al. (2020) further specify that in spatial dysgraphia, oral spelling and fine-motor tapping speed are preserved, indicating that the spacing irregularities detected in this zone are perceptual-spatial in origin rather than purely motoric. These atypical inter-character intervals are a strong behavioral marker of impaired graphomotor coordination, consistent with Specific Learning Disorder criteria (APA, 2013). Döhla and Heim (2016) additionally note that dysgraphia and dyslexia share spatial-processing deficits that manifest during the physical execution of written output.', 0.9993, 'Potential', NULL, NULL, NULL, '2026-05-10', 0, NULL, '2026-05-10 17:18:02');

-- --------------------------------------------------------

--
-- Table structure for table `students`
--

CREATE TABLE `students` (
  `id` int NOT NULL,
  `name` varchar(100) NOT NULL,
  `student_class` varchar(50) DEFAULT NULL,
  `created_at` datetime DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Dumping data for table `students`
--

INSERT INTO `students` (`id`, `name`, `student_class`, `created_at`) VALUES
(1, 'Ana Reyes', 'Grade 3-A', '2026-02-10 00:08:25'),
(2, 'Ben Cruz', 'Grade 3-A', '2026-02-10 00:08:25'),
(3, 'Carla Domingo', 'Grade 3-B', '2026-02-10 00:08:25'),
(4, 'Diego Santos', 'Grade 3-B', '2026-02-10 00:08:25'),
(5, 'Elena Flores', 'Grade 4-A', '2026-02-10 00:08:25'),
(6, 'Felix Torres', 'Grade 4-A', '2026-02-10 00:08:25'),
(7, 'Gia Mendoza', 'Grade 4-B', '2026-02-10 00:08:25'),
(8, 'Hector Ramos', 'Grade 4-B', '2026-02-10 00:08:25'),
(9, 'Isla Villanueva', 'Grade 5-A', '2026-02-10 00:08:25'),
(10, 'Jose Castillo', 'Grade 5-A', '2026-02-10 00:08:25');

-- --------------------------------------------------------

--
-- Table structure for table `users`
--

CREATE TABLE `users` (
  `id` int NOT NULL,
  `email` varchar(100) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `role` varchar(50) NOT NULL,
  `name` varchar(100) NOT NULL,
  `initials` varchar(10) NOT NULL,
  `created_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `reports`
--
ALTER TABLE `reports`
  ADD PRIMARY KEY (`id`),
  ADD KEY `student_id` (`student_id`);

--
-- Indexes for table `students`
--
ALTER TABLE `students`
  ADD PRIMARY KEY (`id`);

--
-- Indexes for table `users`
--
ALTER TABLE `users`
  ADD PRIMARY KEY (`id`),
  ADD UNIQUE KEY `ix_users_email` (`email`),
  ADD KEY `ix_users_id` (`id`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `reports`
--
ALTER TABLE `reports`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=5;

--
-- AUTO_INCREMENT for table `students`
--
ALTER TABLE `students`
  MODIFY `id` int NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=11;

--
-- AUTO_INCREMENT for table `users`
--
ALTER TABLE `users`
  MODIFY `id` int NOT NULL AUTO_INCREMENT;

--
-- Constraints for dumped tables
--

--
-- Constraints for table `reports`
--
ALTER TABLE `reports`
  ADD CONSTRAINT `reports_ibfk_1` FOREIGN KEY (`student_id`) REFERENCES `students` (`id`) ON DELETE CASCADE;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
