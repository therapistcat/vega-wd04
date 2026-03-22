import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { MdArrowBack, MdLayers, MdGroup, MdCalendarToday, MdLocationOn } from 'react-icons/md';
import api from '../../utils/api';
import ReportDetailsModal from '../../components/ReportDetailsModal';
import { SkeletonStats } from '../../components/Skeleton';

export default function ClusterPage() {
    const { clusterId } = useParams();
    const [cluster, setCluster] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [selectedReport, setSelectedReport] = useState(null);
    const [showModal, setShowModal] = useState(false);

    useEffect(() => {
        const fetchCluster = async () => {
            try {
                const res = await api.get(`/clusters/${clusterId}`);
                setCluster(res.data);
            } catch (err) {
                setError(err.response?.data?.detail || 'Failed to load cluster details');
            } finally {
                setLoading(false);
            }
        };
        fetchCluster();
    }, [clusterId]);

    const openReportById = (complaint) => {
        setSelectedReport(complaint);
        setShowModal(true);
    };

    if (loading) return <div className="page-container"><SkeletonStats /></div>;
    if (error) return <div className="page-container"><div className="dashboard-error">{error}</div></div>;
    if (!cluster) return <div className="page-container">Cluster not found</div>;

    return (
        <div className="page-container">
            <div className="cluster-header">
                <Link to="/citizen/dashboard" className="back-link">
                    <MdArrowBack /> Back to Dashboard
                </Link>
                <div className="cluster-title-wrap">
                    <div className="cluster-icon">
                        <MdLayers size={32} />
                    </div>
                    <div>
                        <h1>Issue Cluster: {cluster.category}</h1>
                        <p className="cluster-meta">
                            <MdLocationOn /> {cluster.location || 'Multiple Locations'}
                        </p>
                    </div>
                    <div className="cluster-status-badge">
                        {cluster.status}
                    </div>
                </div>
            </div>

            <div className="dashboard-grid" style={{ marginBottom: '2rem' }}>
                <div className="card-stat-glass">
                    <div className="card-value-large">{cluster.report_count}</div>
                    <div className="card-label-sub">Total Reports</div>
                    <MdGroup className="stat-bg-icon" />
                </div>
                <div className="card-stat-glass">
                    <div className="card-value-large">{new Date(cluster.created_at).toLocaleDateString()}</div>
                    <div className="card-label-sub">First Reported</div>
                    <MdCalendarToday className="stat-bg-icon" />
                </div>
            </div>

            <div className="table-glass-container">
                <div className="dash-section-head">
                    <h3>Aggregated Complaints</h3>
                    <p>All reports linked to this specific issue are grouped here.</p>
                </div>
                <div className="reddit-feed">
                    {cluster.complaints?.map((c) => (
                        <article 
                            key={c.id} 
                            className="reddit-card clickable" 
                            onClick={() => openReportById(c)}
                        >
                            <div className="feed-main" style={{ paddingLeft: '1rem' }}>
                                <div className="feed-meta">
                                    <span>By {c.reporter?.name || 'Citizen'}</span>
                                    <span>{new Date(c.created_at).toLocaleString()}</span>
                                </div>
                                <h4>{c.description}</h4>
                                <div className="feed-tags">
                                    <span className="tag">Status: {c.status}</span>
                                    <span className="tag">Ward: {c.ward}</span>
                                </div>
                                {c.image_url && (
                                    <div className="feed-image-wrap" style={{ maxHeight: '150px' }}>
                                        <img src={c.image_url} alt="Evidence" />
                                    </div>
                                )}
                            </div>
                        </article>
                    ))}
                </div>
            </div>

            <ReportDetailsModal 
                open={showModal} 
                report={selectedReport} 
                onClose={() => setShowModal(false)} 
            />

            <style jsx>{`
                .cluster-header {
                    margin-bottom: 2rem;
                }
                .back-link {
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    color: var(--primary);
                    text-decoration: none;
                    font-weight: 500;
                    margin-bottom: 1rem;
                    transition: opacity 0.2s;
                }
                .back-link:hover {
                    opacity: 0.8;
                }
                .cluster-title-wrap {
                    display: flex;
                    align-items: center;
                    gap: 1.5rem;
                    background: var(--glass-bg);
                    backdrop-filter: blur(12px);
                    padding: 1.5rem;
                    border-radius: 16px;
                    border: 1px solid var(--glass-border);
                }
                .cluster-icon {
                    width: 64px;
                    height: 64px;
                    background: var(--primary-gradient);
                    border-radius: 12px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: white;
                    box-shadow: 0 8px 16px rgba(59, 130, 246, 0.3);
                }
                .cluster-title-wrap h1 {
                    margin: 0;
                    font-size: 1.8rem;
                    color: var(--text-main);
                }
                .cluster-meta {
                    margin: 0.3rem 0 0;
                    color: var(--text-muted);
                    display: flex;
                    align-items: center;
                    gap: 0.4rem;
                }
                .cluster-status-badge {
                    margin-left: auto;
                    padding: 0.5rem 1rem;
                    background: rgba(16, 185, 129, 0.1);
                    color: #10b981;
                    border-radius: 20px;
                    font-weight: 600;
                    border: 1px solid rgba(16, 185, 129, 0.2);
                }
                .stat-bg-icon {
                    position: absolute;
                    right: 1rem;
                    bottom: 1rem;
                    font-size: 3rem;
                    opacity: 0.05;
                    color: var(--text-main);
                }
                .clickable {
                    cursor: pointer;
                    transition: transform 0.2s, background 0.2s;
                }
                .clickable:hover {
                    transform: translateY(-2px);
                    background: rgba(255, 255, 255, 0.05);
                }
            `}</style>
        </div>
    );
}
