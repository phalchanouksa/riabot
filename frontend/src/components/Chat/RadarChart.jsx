import React, { useMemo } from 'react';
import {
    Leaf, Building, Palette, Briefcase, GraduationCap,
    CircleDollarSign, Landmark, HeartPulse, Coffee,
    Users, Laptop, Scale, Factory, ShoppingCart,
    FlaskConical, Truck, ChevronRight
} from 'lucide-react';

const ICONS = {
    "Agriculture": Leaf,
    "Architecture": Building,
    "Arts": Palette,
    "Business": Briefcase,
    "Education": GraduationCap,
    "Finance": CircleDollarSign,
    "Government": Landmark,
    "Health": HeartPulse,
    "Hospitality": Coffee,
    "Human Services": Users,
    "IT": Laptop,
    "Law": Scale,
    "Manufacturing": Factory,
    "Sales": ShoppingCart,
    "Science": FlaskConical,
    "Transport": Truck
};

const ProfileVisualizer = ({ data }) => {
    const topStrengths = useMemo(() => {
        if (!data) return [];
        return [...data]
            .map(item => ({
                ...item,
                totalScore: (item.interest + item.skill) / 2
            }))
            .sort((a, b) => b.totalScore - a.totalScore)
            .slice(0, 3); // Top 3
    }, [data]);

    if (!topStrengths.length) return null;

    return (
        <div style={{ width: '100%', marginTop: '20px', backgroundColor: 'var(--surface)', padding: '24px', borderRadius: '16px', border: '1px solid var(--border)', boxShadow: '0 4px 20px rgba(0,0,0,0.05)' }}>
            <div style={{ textAlign: 'center', marginBottom: '24px' }}>
                <h3 style={{ margin: 0, fontSize: '1.25rem', color: 'var(--text)', fontWeight: '600' }}>
                    Your Top 3 Dominant Traits 🌟
                </h3>
                <p style={{ margin: '8px 0 0 0', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
                    Based on your answers, these are your natural strengths.
                </p>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {topStrengths.map((trait, index) => {
                    const Icon = ICONS[trait.category] || ChevronRight;

                    return (
                        <div key={trait.category} style={{
                            display: 'flex',
                            alignItems: 'center',
                            padding: '16px',
                            backgroundColor: 'var(--bg)',
                            borderRadius: '12px',
                            border: `1px solid ${index === 0 ? 'var(--primary)' : 'var(--border)'}`,
                            position: 'relative',
                            overflow: 'hidden'
                        }}>
                            {index === 0 && (
                                <div style={{ position: 'absolute', top: 0, left: 0, width: '4px', height: '100%', backgroundColor: 'var(--primary)' }} />
                            )}

                            <div style={{
                                width: '48px', height: '48px',
                                borderRadius: '12px',
                                backgroundColor: index === 0 ? 'rgba(102, 126, 234, 0.1)' : 'var(--surface)',
                                color: index === 0 ? 'var(--primary)' : 'var(--text-muted)',
                                display: 'flex', alignItems: 'center', justifyContent: 'center',
                                marginRight: '16px', flexShrink: 0
                            }}>
                                <Icon size={24} />
                            </div>

                            <div style={{ flexGrow: 1 }}>
                                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                                    <h4 style={{ margin: 0, fontSize: '1rem', color: 'var(--text)' }}>
                                        {index + 1}. {trait.category}
                                    </h4>
                                    <span style={{ fontSize: '0.875rem', fontWeight: 'bold', color: 'var(--text)' }}>
                                        {Math.round(trait.totalScore)}% Match
                                    </span>
                                </div>

                                <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                                    <div style={{ flex: 1 }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                                            <span>Interest</span>
                                            <span>{trait.interest}%</span>
                                        </div>
                                        <div style={{ width: '100%', height: '6px', backgroundColor: 'var(--surface)', borderRadius: '3px', overflow: 'hidden' }}>
                                            <div style={{ width: `${trait.interest}%`, height: '100%', backgroundColor: '#667eea', borderRadius: '3px' }} />
                                        </div>
                                    </div>

                                    <div style={{ flex: 1 }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.7rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
                                            <span>Skill</span>
                                            <span>{trait.skill}%</span>
                                        </div>
                                        <div style={{ width: '100%', height: '6px', backgroundColor: 'var(--surface)', borderRadius: '3px', overflow: 'hidden' }}>
                                            <div style={{ width: `${trait.skill}%`, height: '100%', backgroundColor: '#10b981', borderRadius: '3px' }} />
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    );
                })}
            </div>
        </div>
    );
};

export default ProfileVisualizer;
