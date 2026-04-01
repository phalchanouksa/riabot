import React from 'react';

const UniversityRecommendationsCard = ({ data }) => {
  if (!Array.isArray(data) || data.length === 0) {
    return null;
  }

  return (
    <div className="university-results-card">
      <div className="university-results-header">
        <h3>មុខជំនាញនៅសាកលវិទ្យាល័យអង្គរ</h3>
        <p>បង្ហាញតែជម្រើសដែលមានបង្រៀននៅ Angkor University ប៉ុណ្ណោះ។</p>
      </div>

      <div className="university-results-groups">
        {data.map((group, index) => (
          <section key={`${group.generic_major}-${index}`} className="university-result-group">
            <div className="university-result-group-header">
              <div>
                <span className="university-result-rank">{index + 1}</span>
                <h4>{group.generic_major}</h4>
              </div>
              <span className="university-result-confidence">
                {Math.round((group.confidence || 0) * 100)}%
              </span>
            </div>

            <div className="university-program-list">
              {group.programs.map((program, programIndex) => (
                <article
                  key={`${group.generic_major}-${program.name}-${programIndex}`}
                  className="university-program-card"
                >
                  <h5>{program.name}</h5>
                  {program.careers?.length > 0 && (
                    <div className="university-career-section">
                      <span className="university-career-label">Career Paths</span>
                      <ul>
                        {program.careers.map((career, careerIndex) => (
                          <li key={`${program.name}-${career}-${careerIndex}`}>{career}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </article>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
};

export default UniversityRecommendationsCard;
