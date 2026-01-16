import { eq, desc, gt, lt, and, sql } from 'drizzle-orm';
import { db } from '../index';
import {
  evolutionGenerations,
  features,
  mutations,
  type EvolutionGeneration,
  type NewEvolutionGeneration,
  type Feature,
  type NewFeature,
  type Mutation,
  type NewMutation,
} from '../schema';
import { cacheInvalidation, CacheTTL, cacheManager, domainCache } from '../cache';
import { CacheKeys } from '../cache';

/**
 * Evolution Repository
 * Manages evolution generations, features, and mutations with complex queries
 */
export class EvolutionRepository {
  // ==================== Generation Methods ====================

  /**
   * Create a new evolution generation
   */
  async createGeneration(data: NewEvolutionGeneration): Promise<EvolutionGeneration> {
    const [generation] = await db.insert(evolutionGenerations).values(data).returning();
    cacheInvalidation.onEvolutionChange();
    return generation;
  }

  /**
   * Get the latest evolution generation (cached with 1m TTL)
   */
  async getLatestGeneration(): Promise<EvolutionGeneration | null> {
    const cacheKey = CacheKeys.EVOLUTION_GENERATION('latest');
    const cached = cacheManager.get<EvolutionGeneration>(cacheKey);

    if (cached !== null) {
      return cached;
    }

    const [generation] = await db
      .select()
      .from(evolutionGenerations)
      .orderBy(desc(evolutionGenerations.generationNumber))
      .limit(1);
    const result = generation || null;

    if (result) {
      cacheManager.set(cacheKey, result, CacheTTL.EVOLUTION_DATA);
    }

    return result;
  }

  /**
   * Get generations within a range
   */
  async getGenerationsInRange(startGeneration: number, endGeneration: number): Promise<EvolutionGeneration[]> {
    return db
      .select()
      .from(evolutionGenerations)
      .where(
        and(
          gt(evolutionGenerations.generationNumber, startGeneration - 1),
          lt(evolutionGenerations.generationNumber, endGeneration + 1)
        )
      )
      .orderBy(evolutionGenerations.generationNumber);
  }

  /**
   * Get generation by generation number
   */
  async getGenerationByNumber(generationNumber: number): Promise<EvolutionGeneration | null> {
    const [generation] = await db
      .select()
      .from(evolutionGenerations)
      .where(eq(evolutionGenerations.generationNumber, generationNumber))
      .limit(1);
    return generation || null;
  }

  /**
   * Get generation by ID
   */
  async getGenerationById(id: number): Promise<EvolutionGeneration | null> {
    const [generation] = await db
      .select()
      .from(evolutionGenerations)
      .where(eq(evolutionGenerations.id, id))
      .limit(1);
    return generation || null;
  }

  // ==================== Feature Methods ====================

  /**
   * Create a new feature
   */
  async createFeature(data: NewFeature): Promise<Feature> {
    const [feature] = await db.insert(features).values(data).returning();
    cacheInvalidation.onEvolutionChange();
    return feature;
  }

  /**
   * Get feature by ID
   */
  async getFeatureById(featureId: string): Promise<Feature | null> {
    const [feature] = await db
      .select()
      .from(features)
      .where(eq(features.featureId, featureId))
      .limit(1);
    return feature || null;
  }

  /**
   * Get top features by success rate
   */
  async getTopFeatures(limit: number = 10): Promise<Feature[]> {
    return db
      .select()
      .from(features)
      .orderBy(desc(features.successRate))
      .limit(limit);
  }

  /**
   * Get features by minimum success rate
   */
  async getFeaturesByMinSuccessRate(minSuccessRate: number): Promise<Feature[]> {
    return db
      .select()
      .from(features)
      .where(gt(features.successRate, minSuccessRate - 0.0001))
      .orderBy(desc(features.successRate));
  }

  /**
   * Update feature statistics
   */
  async updateFeatureStats(
    featureId: string,
    stats: {
      successRate?: number;
      totalUses?: number;
      wins?: number;
      losses?: number;
      avgPnl?: number;
    }
  ): Promise<Feature | null> {
    const [feature] = await db
      .update(features)
      .set({
        ...stats,
        updatedAt: new Date(),
      })
      .where(eq(features.featureId, featureId))
      .returning();
    cacheInvalidation.onEvolutionChange();
    return feature || null;
  }

  /**
   * Record feature usage result (updates stats automatically)
   */
  async recordFeatureResult(
    featureId: string,
    won: boolean,
    pnl: number
  ): Promise<Feature | null> {
    // First get current feature stats
    const feature = await this.getFeatureById(featureId);
    if (!feature) return null;

    // Calculate new stats
    const totalUses = feature.totalUses + 1;
    const wins = won ? feature.wins + 1 : feature.wins;
    const losses = won ? feature.losses : feature.losses + 1;
    const successRate = wins / totalUses;
    const avgPnl = (feature.avgPnl * feature.totalUses + pnl) / totalUses;

    return this.updateFeatureStats(featureId, {
      totalUses,
      wins,
      losses,
      successRate,
      avgPnl,
    });
  }

  /**
   * Get all features
   */
  async getAllFeatures(): Promise<Feature[]> {
    return db.select().from(features).orderBy(desc(features.successRate));
  }

  // ==================== Mutation Methods ====================

  /**
   * Create a new mutation
   */
  async createMutation(data: NewMutation): Promise<Mutation> {
    const [mutation] = await db.insert(mutations).values(data).returning();
    cacheInvalidation.onEvolutionChange();
    return mutation;
  }

  /**
   * Get mutations by generation ID
   */
  async getMutationsByGeneration(generationId: number): Promise<Mutation[]> {
    return db
      .select()
      .from(mutations)
      .where(eq(mutations.generationId, generationId))
      .orderBy(mutations.timestamp);
  }

  /**
   * Get mutations by target feature ID
   */
  async getMutationsByFeature(featureId: string): Promise<Mutation[]> {
    return db
      .select()
      .from(mutations)
      .where(eq(mutations.targetFeatureId, featureId))
      .orderBy(desc(mutations.timestamp));
  }

  /**
   * Get successful mutations
   */
  async getSuccessfulMutations(limit: number = 50): Promise<Mutation[]> {
    return db
      .select()
      .from(mutations)
      .where(eq(mutations.success, true))
      .orderBy(desc(mutations.fitnessImprovement))
      .limit(limit);
  }

  /**
   * Get failed mutations
   */
  async getFailedMutations(limit: number = 50): Promise<Mutation[]> {
    return db
      .select()
      .from(mutations)
      .where(eq(mutations.success, false))
      .orderBy(desc(mutations.timestamp))
      .limit(limit);
  }

  /**
   * Get mutation statistics for a generation
   */
  async getMutationStatsForGeneration(generationId: number): Promise<{
    totalMutations: number;
    successfulMutations: number;
    failedMutations: number;
    successRate: number;
    avgFitnessImprovement: number;
  } | null> {
    const generationMutations = await this.getMutationsByGeneration(generationId);

    if (generationMutations.length === 0) {
      return {
        totalMutations: 0,
        successfulMutations: 0,
        failedMutations: 0,
        successRate: 0,
        avgFitnessImprovement: 0,
      };
    }

    const successfulMutations = generationMutations.filter((m) => m.success).length;
    const failedMutations = generationMutations.length - successfulMutations;
    const successRate = successfulMutations / generationMutations.length;
    const avgFitnessImprovement =
      generationMutations.reduce((sum, m) => sum + m.fitnessImprovement, 0) /
      generationMutations.length;

    return {
      totalMutations: generationMutations.length,
      successfulMutations,
      failedMutations,
      successRate,
      avgFitnessImprovement,
    };
  }

  // ==================== Analysis Methods ====================

  /**
   * Get overall evolution statistics
   */
  async getEvolutionStats(): Promise<{
    totalGenerations: number;
    totalFeatures: number;
    totalMutations: number;
    latestGeneration: EvolutionGeneration | null;
    avgFeatureSuccessRate: number;
    mutationSuccessRate: number;
  }> {
    const [generationsCount] = await db
      .select({ count: sql<number>`count(*)` })
      .from(evolutionGenerations);

    const [featuresCount] = await db
      .select({ count: sql<number>`count(*)` })
      .from(features);

    const [mutationsCount] = await db
      .select({ count: sql<number>`count(*)` })
      .from(mutations);

    const [avgSuccessRate] = await db
      .select({ avg: sql<number>`avg(success_rate)` })
      .from(features);

    const [successfulMutations] = await db
      .select({ count: sql<number>`count(*)` })
      .from(mutations)
      .where(eq(mutations.success, true));

    const latestGeneration = await this.getLatestGeneration();

    return {
      totalGenerations: generationsCount.count,
      totalFeatures: featuresCount.count,
      totalMutations: mutationsCount.count,
      latestGeneration,
      avgFeatureSuccessRate: avgSuccessRate.avg || 0,
      mutationSuccessRate: mutationsCount.count > 0 ? successfulMutations.count / mutationsCount.count : 0,
    };
  }

  /**
   * Get feature performance ranking
   */
  async getFeaturePerformanceRanking(): Promise<
    Array<{
      featureId: string;
      featureName: string;
      successRate: number;
      totalUses: number;
      avgPnl: number;
      rank: number;
    }>
  > {
    const allFeatures = await this.getTopFeatures();
    return allFeatures.map((feature, index) => ({
      featureId: feature.featureId,
      featureName: feature.featureName,
      successRate: feature.successRate,
      totalUses: feature.totalUses,
      avgPnl: feature.avgPnl,
      rank: index + 1,
    }));
  }
}

/**
 * Singleton instance of EvolutionRepository
 */
export const evolutionRepository = new EvolutionRepository();
